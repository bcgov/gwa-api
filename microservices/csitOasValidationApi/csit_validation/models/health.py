from __future__ import annotations
import pprint
import re  # noqa: F401
import json
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, StrictStr
from typing import Any, ClassVar, Dict, List, Optional


class HealthStatus(str, Enum):
    """Standardized health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


HEALTH_DETAILS_EXAMPLE = {
    "spectral": {
        "status": "healthy"
    },
}

class HealthResponse(BaseModel):
    """
    Detailed health check response for monitoring, dashboards, and humans.
    
    Returns 200 OK even in degraded state (use /readyz for traffic-blocking readiness).
    """
    status: HealthStatus = Field(
        description="Overall service health status. Use 'healthy' when fully operational, "
                    "'degraded' when partially impaired but still serving (reduced capacity/SLO), "
                    "'unhealthy' when critical functions are broken.",
        json_schema_extra={"example": "healthy"}
    )
    
    message: StrictStr = Field(
        description="Short human-readable summary of the current health state.",
        json_schema_extra={"example": "All systems operational"}
    )
    
    timestamp: StrictStr = Field(
        description="ISO 8601 UTC timestamp when this health check was performed.",
        json_schema_extra={"example": "2026-01-26T18:15:42Z"}
    )
    
    components: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Optional breakdown of individual component health. Each key is a component name (e.g. 'spectral', 'cache'). ",
        json_schema_extra={"example": HEALTH_DETAILS_EXAMPLE}
    )

    __properties: ClassVar[List[str]] = [
        "status", "message", "timestamp", "uptime_seconds", "components", "details"
    ]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "message": "All systems operational",
                    "timestamp": "2026-01-26T18:15:42Z",
                    "components": {
                        "spectral": {"status": "healthy"}
                    }
                },
                {
                    "status": "degraded",
                    "message": "Spectral not present",
                    "timestamp": "2026-01-26T18:20:00Z",
                    "components": HEALTH_DETAILS_EXAMPLE,
                }
            ]
        }
    }

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance from a JSON string"""
        return cls.model_validate_json(json_str)

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation using alias, excluding unset fields"""
        return self.model_dump(
            by_alias=True,
            exclude_none=True,
        )

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance from a dict"""
        if obj is None:
            return None
        return cls.model_validate(obj)