from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from clients.deck import convert_to_kong3
from fastapi.logger import logger
import copy

router = APIRouter(
    prefix="",
    tags=["compatibility"],
    responses={404: {"description": "Not found"}},
)

class ValidationResponse(BaseModel):
    kong3_compatible: bool
    conversion_output: str
    kong3_output: dict | None
    kong2_output: dict | None

def convert_to_kong2(kong3_config: dict) -> dict | None:
    """Convert Kong 3.x config back to Kong 2.x format"""
    if not kong3_config:
        return None
        
    # Deep copy to avoid modifying original
    kong2_config = copy.deepcopy(kong3_config)
    
    # Set format version to 2.1
    kong2_config["_format_version"] = "2.1"
    
    # Remove tildes from paths
    if "services" in kong2_config:
        for service in kong2_config["services"]:
            if "routes" in service:
                for route in service["routes"]:
                    if "paths" in route:
                        route["paths"] = [
                            path[1:] if path.startswith("~") else path 
                            for path in route["paths"]
                        ]
    
    return kong2_config

@router.post("/config", response_model=ValidationResponse)
async def validate_kong_config(config: dict) -> ValidationResponse:
    """
    Validates Kong Gateway configuration compatibility with Kong 3.x
    """
    try:
        is_compatible, message, kong3_config = convert_to_kong3(config)
        
        # Convert Kong 3.x config back to Kong 2.x format if we have a valid conversion
        kong2_config = convert_to_kong2(kong3_config) if kong3_config else None
        
        return ValidationResponse(
            kong3_compatible=is_compatible,
            conversion_output=message,
            kong3_output=kong3_config,
            kong2_output=kong2_config
        )
    except Exception as e:
        logger.error("Error validating config: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 