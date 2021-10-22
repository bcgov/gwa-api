import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic.main import BaseModel
from starlette.responses import Response
from clients.ocp_routes import get_gwa_ocp_routes, kubectl_delete, prepare_apply_routes, apply_routes, prepare_mismatched_routes, delete_routes
from logger.utils import timeit
from config import settings
import traceback
import os
from auth.basic_auth import verify_credentials
import sys
from datetime import datetime
from fastapi.logger import logger
from config import settings

router = APIRouter(
    prefix="/namespaces/{namespace}/routes",
    tags=["routes"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_credentials)]
)


class OCPRoute(BaseModel):
    hosts: list
    select_tag: str
    ns_attributes: dict


@router.put("", status_code=201)
def add_routes(namespace: str, route: OCPRoute):

    try:
        source_folder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), namespace)
        os.makedirs(source_folder, exist_ok=False)
        route_count = prepare_apply_routes(namespace, route.select_tag, route.hosts,
                                           source_folder)
        logger.debug("[%s] - Prepared %s routes" % (namespace, route_count))
        if route_count > 0:
            apply_routes(source_folder)
            logger.debug("[%s] - Applied %s routes" % (namespace, route_count))
        route_count = prepare_mismatched_routes(route.select_tag, route.hosts, source_folder)
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


@router.delete("/{name}", status_code=204)
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


@router.post("/sync", status_code=200)
async def verify_and_create_routes(namespace: str, request: Request):

    source_routes = await request.json()

    existing_routes_json = get_gwa_ocp_routes(extralabels="aps-namespace=%s" % namespace)

    existing_routes = []

    for route in existing_routes_json:
        existing_routes.append(
            {
                "name": route["metadata"]["name"],
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
            hosts_by_st_dict = group_hosts_by_tag(insert_batch)

            for st in hosts_by_st_dict:
                prepare_apply_routes(namespace, st, hosts_by_st_dict[st], source_folder)
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


def group_hosts_by_tag(data):
    select_tags_dict = {}
    for route in data:
        if route["selectTag"] not in select_tags_dict:
            select_tags_dict[route["selectTag"]] = []
        select_tags_dict[route["selectTag"]].append(route['host'])

    return select_tags_dict
