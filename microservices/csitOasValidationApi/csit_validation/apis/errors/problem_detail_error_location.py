from __future__ import annotations
import json
from enum import Enum
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue



try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class ProblemDetailErrorLocation(str, Enum):
    """
    The location on the HTTP request for which a problem has been detected. (e.g., body, query, header, path, cookie).
    """

    """
    allowed enum values
    """
    BODY = 'body'
    QUERY = 'query'
    HEADER = 'header'
    PATH = 'path'
    COOKIE = 'cookie'
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        
        # gets {"type": "string", "enum": [...], ...}
        json_schema = handler(core_schema)  

        # Add (or override) examples cleanly
        json_schema["examples"] = ["body"]

        return json_schema

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of ProblemDetailErrorLocation from a JSON string"""
        return cls(json.loads(json_str))


