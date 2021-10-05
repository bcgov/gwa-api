import uuid
from fastapi import APIRouter, Depends
from fastapi.logger import logger
from fastapi.exceptions import HTTPException
from pydantic.main import BaseModel
from starlette.responses import Response
from clients.ocp_secret import prep_and_apply_secret
from auth.auth import validate_permissions
from clients.ocp_routes import kubectl_delete
import traceback
import sys
import os

router = APIRouter(
    prefix="/namespaces/{namespace}/secrets",
    tags=["secrets"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(validate_permissions)]
)


class Secret(BaseModel):
    content: str


@router.put("", status_code=201)
def add_secret(namespace: str, secret: Secret):
    try:
        select_tag = "ns.%s" % namespace
        source_folder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), namespace)
        os.makedirs(source_folder, exist_ok=False)
        prep_and_apply_secret(namespace, select_tag, secret.content, source_folder)
    except Exception as ex:
        traceback.print_exc()
        logger.error("%s - %s" % (namespace, "Failed adding secret"))
        raise HTTPException(status_code=400, detail=str(ex))
    except:
        traceback.print_exc()
        logger.error("%s - %s" % (namespace, "Failed adding secret"))
        raise HTTPException(status_code=400, detail=str(sys.exc_info()[0]))
    return {"message": "created"}


@router.delete("/{name}", status_code=204)
def delete_secret(name: str):
    try:
        kubectl_delete('Secret', name)
    except Exception as ex:
        traceback.print_exc()
        logger.error("Failed deleting secret %s" % name)
        raise HTTPException(status_code=400, detail=str(ex))
    except:
        traceback.print_exc()
        logger.error("Failed deleting secret %s" % name)
        raise HTTPException(status_code=400, detail=str(sys.exc_info()[0]))
    return Response(status_code=204)
