from __future__ import annotations
import pprint
import json

from enum import Enum


from pydantic import BaseModel, GetJsonSchemaHandler, Field, StrictStr, field_validator
from pydantic.json_schema import JsonSchemaValue
from typing import Any, ClassVar, Dict, List
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

class Severity(str, Enum):
    error = "error"
    warn = "warn"
    info = "info"
    hint = "hint"
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        # Let Pydantic generate the base schema: {"type": "string", "enum": ["error", "warn", ...]}
        json_schema = handler(core_schema)

        # Add the example(s) at the schema level (sibling to "enum")
        json_schema["examples"] = ["error"]

        return json_schema

class Result(BaseModel):
    code: StrictStr = Field(description="Rule code or identifier")
    message: StrictStr = Field(description="Human-readable description of the issue")
    severity: Severity = Field(description="Severity level of the result")
    path: List[str] = Field(description="JSONPath-like location in the document where the issue occurred")
    __properties: ClassVar[List[str]] = ["code", "message", "severity", "path"]

    @field_validator('severity')
    def severity_validate_enum(cls, value):
        """Validates the enum"""
        if value not in ('error', 'warn', 'info', 'hint',):
            raise ValueError("must be one of enum values ('error', 'warn', 'info', 'hint')")
        return value

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "json_schema_extra": {
            "examples": [
                {
                    "code": "operation-id-camel-case",
                    "message": "operationId should be camelCase (starts with lowercase letter, no separators)",
                    "path": ["paths", "/users/{id}", "get", "operationId"],
                    "severity": "error"
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
        """Create an instance of Result from a JSON string"""
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
            exclude={},
            exclude_none=True,
        )
        # No need for special handling of path — it's just List[str]
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of Result from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        # Simple direct mapping — path is List[str]
        _obj = cls.model_validate({
            "code": obj.get("code"),
            "message": obj.get("message"),
            "severity": obj.get("severity"),
            "path": obj.get("path") if obj.get("path") is not None else None,
        })
        return _obj