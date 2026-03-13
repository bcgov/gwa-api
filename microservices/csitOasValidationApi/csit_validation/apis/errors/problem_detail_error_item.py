from __future__ import annotations
import pprint
import json




from pydantic import BaseModel, Field, StrictStr
from typing import Any, ClassVar, Dict, List, Optional
from csit_validation.apis.errors.problem_detail_error_location import ProblemDetailErrorLocation
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

CONSTRAINTS_JSON_SCHEMA_EXTRA = {
    "example": {
        "minLength": 9,
        "pattern": "^\\d{9}$"
    }
}

class ProblemDetailErrorItem(BaseModel):
    """
    Represents a single detailed error within a Problem Details response (RFC 9457). Provides granular information about what went wrong in the request, typically used in validation, semantic, or business-rule failures.
    """
    location: ProblemDetailErrorLocation = Field(description="The part of the HTTP request where the error occurred (body, query, path, header, etc.). Helps clients quickly locate the problematic input.")
    code: StrictStr = Field(description="A machine-readable error code that identifies the specific type of error. Should be stable and documented for programmatic handling. Follows the 'application/problem+json' error code pattern from RFC 9457.", json_schema_extra={"example":"INVALID_LINE_NUMBER"})
    message: StrictStr = Field(description="A short, human-readable summary of the error suitable for display to end-users or in logs. Should be clear and concise (RFC 9457 recommends avoiding technical jargon where possible).", json_schema_extra={"example":"Line number does not exist in the specified document"})
    type: StrictStr = Field(description="A URI reference or tag that identifies the problem type (RFC 9457 'type' field). Often used to categorize errors (e.g., validation, authorization, business-rule). When using tags instead of URIs, prefix with 'tag:' is a common convention.", json_schema_extra={"example":"tag:validation-error"})
    field: Optional[StrictStr] = Field(default=None, description="The name of the specific field/property in the request that caused the error (when applicable). Useful for form-based or structured input validation.", json_schema_extra={"example":"taxYear"})
    detail: Optional[StrictStr] = Field(default=None, description="A more detailed human-readable explanation of the error, providing additional context beyond the short message (maps to RFC 9457 'detail' field). May include contextual information or suggested corrections.", json_schema_extra={"example":"Line 99999 is not present in T1 General for 2024"})
    received: Optional[StrictStr] = Field(default=None, description="The actual value received by the server that caused the error (useful for debugging and helping clients understand what was invalid).", json_schema_extra={"example":"99999"})
    pointer: Optional[StrictStr] = Field(default=None, description="JSON Pointer (RFC 6901) to the exact location of the error within the request body (e.g., '#/lineNumbers/0'). Highly recommended for deep/nested validation errors (aligns with RFC 9457 best practices).", json_schema_extra={"example":"#/lineNumbers/1"})
    constraints: Optional[Dict[str, Any]] = Field(default=None, description="Optional object containing validation constraint violations (e.g., minLength, pattern, enum values). Keys are constraint names, values are expected values or descriptions. Useful for schema-based validation libraries.", json_schema_extra=CONSTRAINTS_JSON_SCHEMA_EXTRA)
    __properties: ClassVar[List[str]] = ["location", "code", "message", "type", "field", "detail", "received", "pointer", "constraints"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "json_schema_extra" : {
            "examples": [
                {
                "location": "body",
                "code": "REQUIRED_FIELD_MISSING",
                "message": "Missing required identifier",
                "type": "tag:validation-error",
                "pointer": "#/identifier",
                "detail": "One of 'sin' or both 'fullLegalName' and 'birthDate' must be provided",
                "received": "",
                "field": "individual"
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
        """Create an instance of ProblemDetailErrorItem from a JSON string"""
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
        # set to None if var_field (nullable) is None
        # and model_fields_set contains the field
        if self.var_field is None and "var_field" in self.model_fields_set:
            _dict['field'] = None

        # set to None if detail (nullable) is None
        # and model_fields_set contains the field
        if self.detail is None and "detail" in self.model_fields_set:
            _dict['detail'] = None

        # set to None if received (nullable) is None
        # and model_fields_set contains the field
        if self.received is None and "received" in self.model_fields_set:
            _dict['received'] = None

        # set to None if pointer (nullable) is None
        # and model_fields_set contains the field
        if self.pointer is None and "pointer" in self.model_fields_set:
            _dict['pointer'] = None

        # set to None if constraints (nullable) is None
        # and model_fields_set contains the field
        if self.constraints is None and "constraints" in self.model_fields_set:
            _dict['constraints'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of ProblemDetailErrorItem from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "location": obj.get("location"),
            "code": obj.get("code"),
            "message": obj.get("message"),
            "type": obj.get("type"),
            "field": obj.get("field"),
            "detail": obj.get("detail"),
            "received": obj.get("received"),
            "pointer": obj.get("pointer"),
            "constraints": obj.get("constraints")
        })
        return _obj


