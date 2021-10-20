import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic.main import BaseModel
from starlette.responses import Response
from clients.ocp_routes import get_gwa_ocp_routes, kubectl_delete, prepare_apply_routes, apply_routes, prepare_mismatched_routes, delete_routes
from logger.utils import timeit
from services.namespaces import NamespaceService
from config import settings
import traceback
import os
from auth.auth import validate_permissions, validate_token
import sys
from datetime import datetime
from fastapi.logger import logger
from config import settings

router = APIRouter(
    prefix="",
    tags=["routes"],
    responses={404: {"description": "Not found"}},
)


class RouteRequest(BaseModel):
    hosts: list
    select_tag: str


@router.put("/namespaces/{namespace}/routes", status_code=201, dependencies=[Depends(validate_permissions)])
def add_routes(namespace: str, route: RouteRequest):
    hosts = route.hosts
    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    # if settings.hostTransformation['enabled']:
    #     # Transform Hosts
    #     new_hosts = []
    #     for host in hosts:
    #         new_hosts.append(transform_host(host))
    #     hosts = new_hosts
    try:
        validate_hosts(ns_attributes, hosts)
    except Exception as ex:
        traceback.print_exc()
        logger.error("%s - %s" % (namespace, " Host Validation Errors: %s" % ex))
        raise HTTPException(status_code=403, detail="Validation Errors:\n%s" % ex)
    try:
        source_folder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), namespace)
        os.makedirs(source_folder, exist_ok=False)
        route_count = prepare_apply_routes(namespace, route.select_tag, hosts,
                                           source_folder, get_data_plane(ns_attributes))
        logger.debug("[%s] - Prepared %s routes" % (namespace, route_count))
        if route_count > 0:
            apply_routes(source_folder)
            logger.debug("[%s] - Applied %s routes" % (namespace, route_count))
        route_count = prepare_mismatched_routes(route.select_tag, hosts, source_folder)
        logger.debug("[%s] - Prepared %d deletions" % (namespace, route_count))
        if route_count > 0:
            logger.debug("[%s] - Prepared deletions" % (namespace))
            delete_routes(source_folder)
    except Exception as ex:
        traceback.print_exc()
        logger.error("[%s] Error creating routes. %s" % (namespace, ex))
        raise HTTPException(status_code=400, detail="[%s] Error creating routes. %s" % (namespace, ex))
    except:
        traceback.print_exc()
        logger.error("[%s] Error creating routes. %s" % (namespace, sys.exc_info()[0]))
        raise HTTPException(status_code=400, detail="[%s] Error creating routes. %s" % (namespace, sys.exc_info()[0]))
    return {"message": "created"}


@router.delete("/namespaces/{namespace}/routes/{name}", status_code=204, dependencies=[Depends(validate_permissions)])
def delete_route(name: str):
    try:
        kubectl_delete('route', name)
    except Exception as ex:
        traceback.print_exc()
        logger.error("Failed deleting route %s" % name)
        raise HTTPException(status_code=400, detail=str(ex))
    except:
        traceback.print_exc()
        logger.error("Failed deleting route %s" % name)
        raise HTTPException(status_code=400, detail=str(sys.exc_info()[0]))
    return Response(status_code=204)


@router.post("/sync/routes", status_code=200, dependencies=[Depends(validate_token)])
async def verify_and_create_routes(request: Request):

    source_routes = await request.json()

    existing_routes_json = get_gwa_ocp_routes()

    existing_routes = []

    for route in existing_routes_json:
        existing_routes.append(
            {
                "name": route["metadata"]["name"],
                "namespace": route["metadata"]["labels"]["aps-namespace"],
                "selectTag": route["metadata"]["labels"]["aps-select-tag"],
                "host": route["spec"]["host"]
            }
        )

    insert_batch = [x for x in source_routes if x not in existing_routes]
    delete_batch = [y for y in existing_routes if y not in source_routes]

    logger.debug("insert batch: " + str(insert_batch))

    logger.debug("delete batch: " + str(delete_batch))

    try:
        if len(insert_batch) > 0:
            logger.debug("Creating %s routes" % (len(insert_batch)))
            source_folder = "%s/%s" % ('/tmp/sync', f'{datetime.now():%Y%m%d%H%M%S}')
            os.makedirs(source_folder, exist_ok=False)
            routes_by_ns_dict = group_hosts_by_ns(insert_batch)
            ns_svc = NamespaceService()
            for ns in routes_by_ns_dict:
                ns_attributes = ns_svc.get_namespace_attributes(ns)
                data_plane = get_data_plane(ns_attributes)
                for route in routes_by_ns_dict[ns]:
                    select_tag = route["selectTag"]
                    hosts = [route["host"]]
                    prepare_apply_routes(ns, select_tag, hosts, source_folder, data_plane)
                    apply_routes(source_folder)
    except Exception as ex:
        traceback.print_exc()
        logger.error("Error creating routes. %s" % (ex))
        raise HTTPException(status_code=400, detail="Error creating routes. %s" % (ex))
    except:
        traceback.print_exc()
        logger.error("Error creating routes. %s" % (sys.exc_info()[0]))
        raise HTTPException(status_code=400, detail="Error creating routes. %s" % (sys.exc_info()[0]))

    if len(delete_batch) > 0:
        logger.debug("Deleting %s routes" % (len(insert_batch)))
        for route in delete_batch:
            try:
                kubectl_delete('route', route["name"])
            except Exception as ex:
                traceback.print_exc()
                logger.error("Failed deleting route %s" % route["name"])
                raise HTTPException(status_code=400, detail=str(ex))
            except:
                traceback.print_exc()
                logger.error("Failed deleting route %s" % route["name"])
                raise HTTPException(status_code=400, detail=str(sys.exc_info()[0]))
    return Response(status_code=200)


@timeit
def validate_hosts(ns_attributes, hosts):
    allowed_domains = []
    for domain in ns_attributes.get('perm-domains', ['.api.gov.bc.ca']):
        allowed_domains.append("%s" % domain)
    errors = []
    reserved_hosts = []
    gwa_routes = get_gwa_ocp_routes()
    for route in gwa_routes:
        reserved_hosts.append(route["spec"]["host"])
    reserved_hosts = list(set(reserved_hosts))

    for host in hosts:
        # checking any element of hosts in reserved hosts
        if host in reserved_hosts:
            errors.append("The host %s is already used in another namespace" % host)
        if host_ends_with_one_of_list(host, allowed_domains) is False:
            errors.append("Host invalid: %s.  Route hosts must end with one of [%s] for this namespace." % (
                host, ','.join(allowed_domains)))
    if len(errors) != 0:
        raise Exception('\n'.join(errors))


def host_ends_with_one_of_list(a_str, a_list):
    for item in a_list:
        if a_str.endswith(item):
            return True
    return False


def is_host_transform_enabled():
    return settings.hostTransformation['enabled'] is True


def group_hosts_by_ns(data):
    routes_by_ns = {}
    for route_obj in data:
        if route_obj['namespace'] not in routes_by_ns:
            routes_by_ns[route_obj['namespace']] = []
        routes_by_ns[route_obj['namespace']].append(route_obj)
    return routes_by_ns


def get_data_plane(ns_attributes):
    default_data_plane = settings.dataPlane
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]
