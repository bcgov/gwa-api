import uuid
import base64
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic.main import BaseModel
from starlette.responses import Response
from clients.ocp_routes import get_gwa_ocp_routes, kubectl_delete, prepare_apply_routes, apply_routes, prepare_mismatched_routes, delete_routes
from clients.ocp_services import get_gwa_ocp_service_secrets, prepare_apply_services, apply_services, prepare_mismatched_services, delete_services
import traceback
import os
from auth.basic_auth import verify_credentials
import sys
import secrets
from datetime import datetime
from fastapi.logger import logger
from config import settings
from typing import Optional
import socket
import requests
from urllib.parse import urlparse
import urllib3
import certifi

router = APIRouter(
    prefix="",
    tags=["routes"],
    responses={404: {"description": "Not found"}},
)


class OCPRoute(BaseModel):
    hosts: list
    select_tag: str
    ns_attributes: dict
    overrides: dict | None = None
    certificates: list | None = None


class BulkSyncRequest(BaseModel):
    # Name of the Route
    name: str
    # Namespace with optional qualifier
    selectTag: str
    # Dataplane (Kubernetes Service name for the particular Kong data plane)
    dataPlane: str
    # Route host
    host: str
    # Indicator of whether session cookies should be enabled by the Kube-API
    sessionCookieEnabled: bool
    # Data class for Emerald Cluster routes
    dataClass: str
    # SSL Certificate serial number for custom domains
    sslCertificateSerialNumber: str


class ServiceStatusRequest(BaseModel):
    services: list
    routes: list
    conf: dict

    
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
    except SystemExit as ex:
        raise ex
    except BaseException:
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
                                           source_folder, get_data_plane(route.ns_attributes), ns_template_version, route.overrides,
                                           route.certificates)
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
    except SystemExit as ex:
        raise ex
    except BaseException:
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
    except SystemExit as ex:
        raise ex
    except BaseException:
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

@router.get("/namespaces/{namespace}/service-status", status_code=200, dependencies=[Depends(verify_credentials)])
def get_service_status(namespace: str, service_payload: ServiceStatusRequest):
    logger.debug("[%s] get_service_status" % namespace)

    services = service_payload.services
    routes = service_payload.routes
    conf = service_payload.conf

    response = []

    for service in services:
        url = build_url (service)
        status = "UP"
        reason = ""

        actual_host = None
        host = None
        for route in routes:
            if route['service']['id'] == service['id'] and 'hosts' in route:
                actual_host = route['hosts'][0]
                if route['preserve_host']:
                    host = clean_host(actual_host, conf)

        try:
            addr = socket.gethostbyname(service['host'])
            logger.info("Address = %s" % addr)
        except:
            status = "DOWN"
            reason = "DNS"

        if status == "UP":
            try:
                headers = {}
                if host is None or service['host'].endswith('.svc'):
                    r = requests.get(url, headers=headers, timeout=3.0)
                    status_code = r.status_code
                else:
                    u = urlparse(url)

                    if host is None:
                        headers['Host'] = u.hostname
                    else:
                        headers['Host'] = host

                    logger.info("GET %-30s %s" % ("%s://%s" % (u.scheme, u.netloc), headers))

                    urllib3.disable_warnings()
                    if u.scheme == "https":
                        pool = urllib3.HTTPSConnectionPool(
                            "%s" % (u.netloc),
                            assert_hostname=host,
                            server_hostname=host,
                            cert_reqs='CERT_NONE',
                            ca_certs=certifi.where()
                        )
                    else:
                        pool = urllib3.HTTPConnectionPool(
                            "%s" % (u.netloc)
                        )
                    req = pool.urlopen(
                        "GET",
                        u.path,
                        headers={"Host": host},
                        assert_same_host=False,
                        timeout=1.0,
                        retries=False
                    )

                    status_code = req.status

                logger.info("Result received!! %d" % status_code)
                if status_code < 400:
                    status =  "UP"
                    reason = "%d Response" % status_code
                elif status_code == 401 or status_code == 403:
                    status = "UP"
                    reason = "AUTH %d" % status_code
                else:
                    status =  "DOWN"
                    reason = "%d Response" % status_code
            except requests.exceptions.Timeout as ex:
                status = "DOWN"
                reason = "TIMEOUT"
            except urllib3.exceptions.ConnectTimeoutError as ex:
                status = "DOWN"
                reason = "TIMEOUT"
            except requests.exceptions.ConnectionError as ex:
                logger.error("ConnError %s" % ex)
                status = "DOWN"
                reason = "CONNECTION"
            except requests.exceptions.SSLError as ex:
                status = "DOWN"
                reason = "SSL"
            except urllib3.exceptions.NewConnectionError as ex:
                logger.error("NewConnError %s" % ex)
                status = "DOWN"
                reason = "CON_ERR"
            except urllib3.exceptions.SSLError as ex:
                logger.error(ex)
                status = "DOWN"
                reason = "SSL_URLLIB3"
            except Exception as ex:
                logger.error(ex)
                traceback.print_exc(file=sys.stdout)
                status = "DOWN"
                reason = "UNKNOWN"

        logger.info("GET %-30s %s" % (url,reason))
        response.append({"name": service['name'], "upstream": url, "status": status, "reason": reason, "host": host, "env_host": actual_host})
    
    return JSONResponse(content={"services_status": response}, status_code=200)

@router.post("/namespaces/{namespace}/routes/sync", status_code=200, dependencies=[Depends(verify_credentials)])
async def verify_and_create_routes(namespace: str, request: Request):

    # We don't use BulkSyncRequest because it will give the error
    # 'object is not subscriptable'
    # source_routes: list[BulkSyncRequest]
    source_routes = await request.json()

    existing_routes_json = get_gwa_ocp_routes(extralabels="aps-namespace=%s" % namespace)

    existing_routes = []

    for route in existing_routes_json:
        existing_routes.append(
            {
                "name": route["metadata"]["name"],
                "selectTag": route["metadata"]["labels"]["aps-select-tag"],
                "host": route["spec"]["host"],
                "dataPlane": route["spec"]["to"]["name"],
                "sessionCookieEnabled": True if route["metadata"]["labels"].get("aps-template-version") == "v1" else False,
                "dataClass": route["metadata"]["annotations"].get("aviinfrasetting.ako.vmware.com/name").split("-")[-1] if route["metadata"]["annotations"].get("aviinfrasetting.ako.vmware.com/name") else None,
                "sslCertificateSerialNumber": route["metadata"]["labels"].get("aps-certificate-serial")
            }
        )

    insert_batch = [x for x in source_routes if not in_list(x, existing_routes)]
    delete_batch = [y for y in existing_routes if not in_list_by_name(y, source_routes)]
        
    logger.debug("insert batch: " + str(insert_batch))

    logger.debug("delete batch: " + str(delete_batch))

    # TODO: We shouldn't assume it is always v2 - caller needs to get
    # this info from ns_attributes
    ns_template_version = "v2"

    inserted_count = 0
    deleted_count = 0

    try:
        if len(insert_batch) > 0:
            source_folder = "%s/%s-%s" % ('/tmp/sync', f'{datetime.now():%Y%m%d%H%M%S}', secrets.token_hex(5))
            os.makedirs(source_folder, exist_ok=False)

            logger.debug("Creating %s routes - tmp %s" % (len(insert_batch), source_folder))

            for route in insert_batch:
                overrides = {}
                if 'sessionCookieEnabled' in route and route['sessionCookieEnabled']:
                    overrides['aps.route.session.cookie.enabled'] = [route['host']]

                if 'dataClass' in route and route['dataClass']:
                    overrides[f'aps.route.dataclass.{route["dataClass"]}'] = [route['host']]
                
                route_count = prepare_apply_routes(namespace, route['selectTag'], [
                                                   route['host']], source_folder, route['dataPlane'], ns_template_version, overrides,
                                                   route['certificates'])
                
                logger.debug("[%s] - Prepared %d routes" % (namespace, route_count))
                apply_routes(source_folder)
                logger.debug("[%s] - Applied %d routes" % (namespace, route_count))

                inserted_count += route_count
    except Exception as ex:
        traceback.print_exc()
        logger.error("Error creating routes. %s" % (ex))
        raise HTTPException(status_code=400, detail="Error creating routes. %s" % (ex))
    except SystemExit as ex:
        raise ex
    except BaseException:
        traceback.print_exc()
        logger.error("Error creating routes. %s" % (sys.exc_info()[0]))
        raise HTTPException(status_code=400, detail="Error creating routes. %s" % (sys.exc_info()[0]))

    if len(delete_batch) > 0:
        logger.debug("Deleting %s routes" % (len(delete_batch)))
        for route in delete_batch:
            try:
                kubectl_delete('route', route["name"])
                logger.debug("[%s] - Deleted route %s" % (namespace, route["name"]))
                deleted_count += 1
            except Exception as ex:
                traceback.print_exc()
                logger.error("Failed deleting route %s" % route["name"])
                raise HTTPException(status_code=400, detail=str(ex))
            except SystemExit as ex:
                raise ex
            except BaseException:
                traceback.print_exc()
                logger.error("Failed deleting route %s" % route["name"])
                raise HTTPException(status_code=400, detail=str(sys.exc_info()[0]))

    return JSONResponse(status_code=200, content={
        "message": "synced",
        "inserted_count": inserted_count,
        "deleted_count": deleted_count
    })

def get_data_plane(ns_attributes):
    default_data_plane = settings.defaultDataPlane
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]

def get_template_version(ns_attributes):
    return ns_attributes.get('template-version', ["v2"])[0]

def in_list(match, list):
    match_ref =  build_ref(match)
    for item in list:
        if build_ref(item) == match_ref:
            return True
    return False

def build_ref(v):
    return f"{v['name']}{v['selectTag']}{v['host']}{v['dataPlane']}{v['sessionCookieEnabled']}{v['dataClass']}{v['sslCertificateSerialNumber']}"

def in_list_by_name(match, list):
    for item in list:
        if item['name'] == match['name']:
            return True
    return False

def build_url (s):
    schema = default(s, "protocol", "http")
    defaultPort = 80
    if schema == "https":
        defaultPort = 443
    host = s['host']
    port = default(s, "port", defaultPort)
    path = default(s, "path", "/")
    if 'url' in s:
        return s['url']
    else:
        return "%s://%s:%d%s" % (schema, host, port, path)

def default (s, key, val):
    if key in s and s[key] is not None:
        return s[key]
    else:
        return val

def clean_host (host, conf):
    if conf['enabled'] is True:
        return host.replace(conf['baseUrl'], 'gov.bc.ca').replace('-data-gov-bc-ca', '.data').replace('-api-gov-bc-ca', '.api').replace('-apps-gov-bc-ca', '.apps')
    else:
        return host
