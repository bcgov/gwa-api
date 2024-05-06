import uuid
import base64
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic.main import BaseModel
from starlette.responses import Response
from clients.ocp_routes import get_gwa_ocp_routes, kubectl_delete, prepare_apply_routes, apply_routes, prepare_mismatched_routes, delete_routes
from clients.ocp_services import get_gwa_ocp_service_secrets, prepare_apply_services, apply_services, prepare_mismatched_services, delete_services
import traceback
import os
from auth.basic_auth import verify_credentials
import sys
from datetime import datetime
from fastapi.logger import logger
from config import settings

router = APIRouter(
    prefix="",
    tags=["routes"],
    responses={404: {"description": "Not found"}},
)


class OCPRoute(BaseModel):
    hosts: list
    select_tag: str
    ns_attributes: dict
    overrides: dict


@router.put("/namespaces/{namespace}/routes", status_code=201, dependencies=[Depends(verify_credentials)])
def add_routes(namespace: str, route: OCPRoute):

    try:
        local_hosts = [a for a in route.hosts if a.endswith(".cluster.local")]

        # do local hosts
        source_folder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), namespace)
        os.makedirs(source_folder, exist_ok=False)
        service_count = prepare_apply_services(namespace, route.select_tag, local_hosts,
                                          source_folder, get_data_plane(route.ns_attributes))
        logger.debug("[%s] - Prepared %s services" % (namespace, service_count))
        if service_count > 0:
            apply_services(source_folder)
            logger.debug("[%s] - Applied %s services" % (namespace, service_count))
        service_count = prepare_mismatched_services(route.select_tag, local_hosts, source_folder)
        logger.debug("[%s] - Prepared %d deletions" % (namespace, service_count))
        if service_count > 0:
            logger.debug("[%s] - Prepared deletions" % (namespace))
            delete_services(source_folder)
    except Exception as ex:
        traceback.print_exc()
        logger.error("[%s] Error creating services. %s" % (namespace, ex))
        raise HTTPException(status_code=400, detail="[%s] Error creating services. %s" % (namespace, ex))
    except:
        traceback.print_exc()
        logger.error("[%s] Error creating routes. %s" % (namespace, sys.exc_info()[0]))
        raise HTTPException(status_code=400, detail="[%s] Error creating routes. %s" % (
            namespace, sys.exc_info()[0]))
          
    try:
        hosts = [a for a in route.hosts if not a.endswith(".cluster.local")]
        
        ns_template_version = get_template_version(route.ns_attributes)

        # do routeable hosts
        source_folder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), namespace)
        os.makedirs(source_folder, exist_ok=False)
        route_count = prepare_apply_routes(namespace, route.select_tag, hosts,
                                           source_folder, get_data_plane(route.ns_attributes), ns_template_version, route.overrides)
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
        raise HTTPException(status_code=400, detail="[%s] Error creating routes. %s" % (
            namespace, sys.exc_info()[0]))
    return {"message": "created"}


@router.delete("/namespaces/{namespace}/routes/{name}", status_code=204, dependencies=[Depends(verify_credentials)])
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

# RETURNS:
# [
#   {
#      "cert": "",
#      "key": "",
#      "snis": [ "name": "abc-host" } ]
#      "tags": [ "gwa.ns.<namespace>"]
#   } 
# ]

@router.get("/namespaces/{namespace}/local_tls", status_code=200, dependencies=[Depends(verify_credentials)])
def get_tls(namespace: str):
    logger.debug("[%s] get_tls" % namespace)
    secrets = get_gwa_ocp_service_secrets(extralabels="aps-namespace=%s" % namespace)
    
    kong_certs = []
    
    for secret in secrets:
        cert = {
          "cert": base64.b64decode(secret['data']['data']['tls.crt']),
          "key": base64.b64decode(secret['data']['data']['tls.key']),
          "tags": [ "gwa.ns.%s" % namespace ],
          "snis": [ secret['host'] ]
        }
        kong_certs.append(cert)
    logger.debug("[%s] returning %d certs" % (namespace, len(kong_certs)))
    return kong_certs

@router.post("/namespaces/{namespace}/routes/sync", status_code=200, dependencies=[Depends(verify_credentials)])
async def verify_and_create_routes(namespace: str, request: Request):

    source_routes = await request.json()

    existing_routes_json = get_gwa_ocp_routes(extralabels="aps-namespace=%s" % namespace)

    existing_routes = []

    for route in existing_routes_json:
        existing_routes.append(
            {
                "name": route["metadata"]["name"],
                "selectTag": route["metadata"]["labels"]["aps-select-tag"],
                "host": route["spec"]["host"],
                "dataPlane": route["spec"]["to"]["name"]
            }
        )

    insert_batch = [x for x in source_routes if x not in existing_routes]

    delete_batch = [y for y in existing_routes if y not in source_routes]

    logger.debug("insert batch: " + str(insert_batch))

    logger.debug("delete batch: " + str(delete_batch))

    # TODO: We shouldn't assume it is always v2 - caller needs to get
    # this info from ns_attributes
    ns_template_version = "v2"

    try:
        if len(insert_batch) > 0:
            logger.debug("Creating %s routes" % (len(insert_batch)))
            source_folder = "%s/%s" % ('/tmp/sync', f'{datetime.now():%Y%m%d%H%M%S}')
            os.makedirs(source_folder, exist_ok=False)

            for route in insert_batch:
                overrides = {}
                if route['session_cookie_enabled']:
                    overrides['aps.route.session.cookie.enabled'] = [ route['host'] ]
                route_count = prepare_apply_routes(namespace, route['selectTag'], [
                                                   route['host']], source_folder, route["dataPlane"], ns_template_version, overrides)
                logger.debug("[%s] - Prepared %d routes" % (namespace, route_count))
                apply_routes(source_folder)
                logger.debug("[%s] - Applied %d routes" % (namespace, route_count))
    except Exception as ex:
        traceback.print_exc()
        logger.error("Error creating routes. %s" % (ex))
        raise HTTPException(status_code=400, detail="Error creating routes. %s" % (ex))
    except:
        traceback.print_exc()
        logger.error("Error creating routes. %s" % (sys.exc_info()[0]))
        raise HTTPException(status_code=400, detail="Error creating routes. %s" % (sys.exc_info()[0]))

    if len(delete_batch) > 0:
        logger.debug("Deleting %s routes" % (len(delete_batch)))
        for route in delete_batch:
            try:
                kubectl_delete('route', route["name"])
                logger.debug("[%s] - Deleted route %s" % (namespace, route["name"]))
            except Exception as ex:
                traceback.print_exc()
                logger.error("Failed deleting route %s" % route["name"])
                raise HTTPException(status_code=400, detail=str(ex))
            except:
                traceback.print_exc()
                logger.error("Failed deleting route %s" % route["name"])
                raise HTTPException(status_code=400, detail=str(sys.exc_info()[0]))
    return Response(status_code=200)


def get_data_plane(ns_attributes):
    default_data_plane = settings.defaultDataPlane
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]

def get_template_version(ns_attributes):
    return ns_attributes.get('template-version', ["v2"])[0]
