from __future__ import annotations
import pprint
import json




from pydantic import BaseModel, Field, StrictInt, StrictStr
from typing import Any, ClassVar, Dict, List, Optional
from typing_extensions import Annotated
from csit_validation.apis.errors.problem_detail_error_item import ProblemDetailErrorItem
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

class ProblemDetailResponse(BaseModel):
    """
    Canonical model for problem details as defined by RFC-9457
    """
    type: StrictStr = Field(description="A URI reference that identifies the problem type", json_schema_extra={"example":"tag:validation-errors"})
    title: StrictStr = Field(description="A short, human-readable summary of the problem type", json_schema_extra={"example":"Bad Request"})
    status: StrictInt = Field(description="A number indicating the HTTP status code generated for this occurrence of the problem", json_schema_extra={"example":400})
    detail: Optional[StrictStr] = Field(default=None, description="A human-readable explanation specific to this occurrence of the problem", json_schema_extra={"example":"One or more validation errors occurred"})
    errors: Annotated[List[ProblemDetailErrorItem], Field(min_length=1)] = Field(description="A list of individual error occurrences found, with details and a pointer to the location of each")
    __properties: ClassVar[List[str]] = ["type", "title", "status", "detail", "errors"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "json_schema_extra" : {
            "examples": [
                {
                    "type": "tag:validation-errors",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": "Invalid line numbers provided",
                    "instance": "/tax-documents/query",
                    "errors": [
                        {
                        "location": "body",
                        "code": "INVALID_LINE_NUMBER",
                        "message": "Line number does not exist in the document",
                        "type": "tag:validation-error",
                        "pointer": "#/lineNumbers/0",
                        "received": "99999"
                        }
                    ]
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
        """Create an instance of ProblemDetailResponse from a JSON string"""
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
        # override the default output from pydantic by calling `to_dict()` of each item in errors (list)
        _items = []
        if self.errors:
            for _item in self.errors:
                if _item:
                    _items.append(_item.to_dict())
            _dict['errors'] = _items
        # set to None if detail (nullable) is None
        # and model_fields_set contains the field
        if self.detail is None and "detail" in self.model_fields_set:
            _dict['detail'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of ProblemDetailResponse from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "type": obj.get("type"),
            "title": obj.get("title"),
            "status": obj.get("status"),
            "detail": obj.get("detail"),
            "errors": [ProblemDetailErrorItem.from_dict(_item) for _item in obj.get("errors")] if obj.get("errors") is not None else None
        })
        return _obj


