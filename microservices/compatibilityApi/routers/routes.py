from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from clients.deck import convert_to_kong3
from fastapi.logger import logger
from utils.transforms import convert_to_kong2, tag_routes
import copy
from typing import List

router = APIRouter(
    prefix="",
    tags=["compatibility"],
    responses={404: {"description": "Not found"}},
)

class ValidationResponse(BaseModel):
    kong3_compatible: bool
    message: str
    failed_routes: List[str]
    kong3_output: dict | None
    kong2_output: dict | None

@router.post("/configs", response_model=ValidationResponse)
async def validate_kong_config(config: dict) -> ValidationResponse:
    """
    Validates Kong Gateway configuration compatibility with Kong 3.x 
    and downgrades config to be Kong 2.x compatible
    """
    try:
        # Tag routes based on Kong 3 compatibility
        tagged_config, failed_routes = tag_routes(config)
        
        # Convert to Kong 3.x format
        is_compatible, _, kong3_config = convert_to_kong3(tagged_config)
        
        # Prepare response message
        if is_compatible:
            message = "Gateway configuration is compatible with Kong 3."
        else:
            message = (
                "\033[1;33m[ Warning ]\033[0m \033[34mKong 3 incompatible routes found.\033[0m\n"
                "APS will soon be updated to use Kong Gateway version 3.\n"
                "Kong 3 requires that regular expressions in route paths start with a '~' character.\n\n"
                "For more information, please visit:\n"
                "https://docs.konghq.com/deck/latest/3.0-upgrade\n\n"
                "Please update the following routes:"
            )
        
        # Convert Kong 3.x config back to Kong 2.x format if we have a valid conversion
        kong2_config = convert_to_kong2(kong3_config) if kong3_config else None
        
        return ValidationResponse(
            kong3_compatible=is_compatible,
            message=message,
            failed_routes=failed_routes,
            kong3_output=kong3_config,
            kong2_output=kong2_config
        )
    except Exception as e:
        logger.error("Error validating config: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 