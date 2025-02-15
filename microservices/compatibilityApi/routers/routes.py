from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from clients.deck import convert_to_kong3
from fastapi.logger import logger

router = APIRouter(
    prefix="",
    tags=["compatibility"],
    responses={404: {"description": "Not found"}},
)

class ValidationResponse(BaseModel):
    kong3_compatible: bool
    conversion_output: str
    original_config: dict
    converted_config: dict | None

@router.post("/config", response_model=ValidationResponse)
async def validate_kong_config(config: dict) -> ValidationResponse:
    """
    Validates Kong Gateway configuration compatibility with Kong 3.x
    """
    try:
        is_compatible, message, converted = convert_to_kong3(config)
        
        return ValidationResponse(
            kong3_compatible=is_compatible,
            conversion_output=message,
            original_config=config,
            converted_config=converted
        )
    except Exception as e:
        logger.error("Error validating config: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 