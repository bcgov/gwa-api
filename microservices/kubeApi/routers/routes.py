import uuid
from fastapi import APIRouter, HTTPException, Depends
from fastapi.logger import logger
from pydantic.main import BaseModel
from starlette.responses import Response
from clients.ocp_routes import get_gwa_ocp_routes, prepare_apply_routes, apply_routes, prepare_mismatched_routes, prepare_delete_route, delete_routes
from services.namespaces import NamespaceService
from config import settings
import traceback
import os
from auth.auth import validate_permissions
import sys

router = APIRouter(
    prefix="/namespaces/{namespace}/routes",
    tags=["routes"],
    dependencies=[Depends(validate_permissions)],
    responses={404: {"description": "Not found"}},
)


class RouteRequest(BaseModel):
    hosts: list


@router.put("", status_code=201)
def add_routes(namespace: str, route: RouteRequest):
    hosts = route.hosts
    select_tag = "ns.%s" % namespace
    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    if settings.hostTransformation['enabled']:
        # Transform Hosts
        new_hosts = []
        for host in hosts:
            new_hosts.append(transform_host(host))
        hosts = new_hosts
    try:
        validate_hosts(ns_attributes, hosts)
    except Exception as ex:
        traceback.print_exc()
        logger.error("%s - %s" % (namespace, " Host Validation Errors: %s" % ex))
        raise HTTPException(status_code=403, detail="Validation Errors:\n%s" % ex)
    try:
        source_folder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), namespace)
        os.makedirs(source_folder, exist_ok=False)
        route_count = prepare_apply_routes(namespace, select_tag, hosts, source_folder)
        logger.debug("[%s] - Prepared %s routes" % (namespace, route_count))
        if route_count > 0:
            apply_routes(source_folder)
            logger.debug("[%s] - Applied %s routes" % (namespace, route_count))
        route_count = prepare_mismatched_routes(select_tag, hosts, source_folder)
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


@router.delete("/{name}", status_code=204)
def delete_route(namespace: str, name: str):
    try:
        select_tag = "ns.%s" % namespace
        source_folder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), namespace)
        os.makedirs(source_folder, exist_ok=False)
        route_count = prepare_delete_route(select_tag, name, source_folder)
        logger.debug("[%s] - Prepared %d deletions" % (namespace, route_count))
        if route_count > 0:
            logger.debug("[%s] - Prepared deletions" % (namespace))
            delete_routes(source_folder)
    except Exception as ex:
        traceback.print_exc()
        logger.error("[%s] Error deleting routes. %s" % (namespace, ex))
        raise HTTPException(status_code=400, detail="[%s] Error deleting route %s. %s" % (namespace, name, ex))
    except:
        traceback.print_exc()
        logger.error("[%s] Error deleting routes. %s" % (namespace, sys.exc_info()[0]))
        raise HTTPException(status_code=400, detail="[%s] Error deleting route %s. %s" % (
            namespace, name, sys.exc_info()[0]))
    return Response(status_code=204)


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
        if a_str.endswith(transform_host(item)):
            return True
    return False


def transform_host(host):
    if is_host_transform_enabled():
        return "%s.%s" % (host.replace('.', '-'), settings.hostTransformation['baseUrl'])
    else:
        return host


def is_host_transform_enabled():
    return settings.hostTransformation['enabled'] is True
