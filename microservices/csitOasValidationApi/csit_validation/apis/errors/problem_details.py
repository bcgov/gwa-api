# api/errors/problem_details.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from fastapi.responses import JSONResponse
from fastapi import status

class ErrorLocation(str, Enum):
    """Standard locations from RFC 9457"""
    BODY   = "body"
    QUERY  = "query"
    HEADER = "header"
    PATH   = "path"
    COOKIE = "cookie"


@dataclass
class ErrorItem:
    """Structured single validation error (RFC 9457 compatible)"""
    location: ErrorLocation
    code: str
    message: str
    type: Optional[str] = "tag:validation-error"
    field: Optional[str] = None
    detail: Optional[str] = None
    received: Optional[Any] = None
    pointer: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "location": self.location.value,
            "code": self.code,
            "message": self.message,
        }
        if self.type is not None:
            d["type"] = self.type
        if self.field is not None:
            d["field"] = self.field
        if self.detail is not None:
            d["detail"] = self.detail
        if self.received is not None:
            d["received"] = self.received
        if self.pointer is not None:
            d["pointer"] = self.pointer
        if self.constraints is not None:
            d["constraints"] = self.constraints
        return d


@dataclass
class ProblemDetail:
    type: str = "tag:validation-errors"
    title: str = "Validation Error"
    status: int = status.HTTP_400_BAD_REQUEST
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: List[ErrorItem] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: ErrorItem) -> None:
        self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
        }
        if self.detail:
            result["detail"] = self.detail
        if self.instance:
            result["instance"] = self.instance
        if self.errors:
            result["errors"] = [e.to_dict() for e in self.errors]
        if self.extra:
            result.update(self.extra)
        return result


def create_problem_response(problem: ProblemDetail) -> JSONResponse:
    """
    Returns a proper RFC 9457 problem detail response with the object at root level.
    This is the recommended way to avoid the unwanted 'detail' wrapper.
    """
    content = problem.to_dict()
    return JSONResponse(
        status_code=content["status"],
        content=content,
        headers={
            "Content-Type": "application/problem+json"
        }
    )