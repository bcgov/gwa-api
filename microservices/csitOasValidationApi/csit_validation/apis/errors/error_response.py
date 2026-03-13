from __future__ import annotations
import pprint
import re  # noqa: F401
import json




from pydantic import BaseModel, Field, StrictStr
from typing import Any, ClassVar, Dict, List, Optional, Annotated
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

DETAILS_JSON_SCHEMA_EXTRA = {
    "example": {
        "correlationId": "req-abc123-xyz",
        "timestamp": "2026-01-16T19:22:00Z"
    }
}

class ErrorResponse(BaseModel):
    """
    Standard error response format for unexpected or server-side errors (e.g., 500 Internal Server Error, 403 Forbidden, 401 Unauthorized, etc.). This is used when a more structured Problem Details response (RFC 9457) is not appropriate or when the error is general rather than validation-specific.
    """
    error: StrictStr = Field(description="A short, machine-readable error code or identifier that categorizes the type of error. This field is stable and intended for programmatic handling by clients (e.g., mapping to specific error-handling logic). Common values include 'internal_error', 'forbidden', 'unauthorized', 'rate_limit_exceeded', etc.", json_schema_extra={"example":"forbidden"})
    message: StrictStr = Field(description="A human-readable summary of the error, suitable for display to end-users or logging. Should be clear, concise, and avoid exposing internal technical details or sensitive information (per security best practices).", json_schema_extra={"example":"You are not authorized to access this resource"})
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional additional context or structured details about the error. This can include extra information useful for debugging (e.g., error codes from downstream systems, correlation IDs, or custom attributes). Use sparingly and avoid including sensitive data.", json_schema_extra=DETAILS_JSON_SCHEMA_EXTRA)
    __properties: ClassVar[List[str]] = ["error", "message", "details"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "json_schema_extra" : {
            "examples": [
                {
                    "error": "forbidden",
                    "message": "You are not authorized to access this resource",
                    "details": {
                        "correlationId": "req-abc123-xyz"
                    }
                }
            ]
        }
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of ErrorResponse from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of ErrorResponse from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "error": obj.get("error"),
            "message": obj.get("message"),
            "details": obj.get("details")
        })
        return _obj


