from fastapi import APIRouter, Depends, Request
from pydantic.main import BaseModel
from starlette.responses import Response
from auth.basic_auth import verify_credentials

router = APIRouter(
    prefix="/noop",
    tags=["routes"],
    responses={404: {"description": "Not found"}},
)


class OCPRoute(BaseModel):
    hosts: list
    select_tag: str
    ns_attributes: dict


@router.put("/namespaces/{namespace}/routes", status_code=201, dependencies=[Depends(verify_credentials)])
def add_routes(namespace: str, route: OCPRoute):
    return {"message": "created"}

@router.delete("/namespaces/{namespace}/routes/{name}", status_code=204, dependencies=[Depends(verify_credentials)])
def delete_route(name: str):
    return Response(status_code=204)

@router.post("/namespaces/{namespace}/routes/sync", status_code=200, dependencies=[Depends(verify_credentials)])
async def verify_and_create_routes(namespace: str, request: Request):
    return Response(status_code=200)
