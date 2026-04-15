from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_LOCATION = Literal["body", "query", "header", "path", "cookie"]


class ValidationError(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "description": "Details of a single request validation error.",
    })

    type: str = Field(..., title="Error Type")
    location: _LOCATION = Field(..., title="Location")
    code: str = Field(..., title="Error Code")
    message: str = Field(..., title="Message")
    input: Any = Field(default=None, title="Input")
    ctx: dict[str, Any] | None = Field(default=None, title="Context")


class HTTPValidationError(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "description": "RFC 7807 Problem Details response returned for request validation errors.",
    })

    type: str = Field(..., description="A URI reference identifying the problem type.")
    title: str = Field(..., description="A short, human-readable summary of the problem type.")
    status: int = Field(..., description="The HTTP status code for this occurrence of the problem.")
    detail: str | None = Field(
        default=None,
        description="A human-readable explanation specific to this occurrence.",
    )
    errors: list[ValidationError] = Field(
        ...,
        min_length=1,
        description="List of individual validation errors.",
    )


class TokenRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "description": "Request body for generating a Step CA one-time token.",
    })

    subject: str
    san: list[str] | None = None


class TokenResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "description": "Response containing the generated one-time Step CA token.",
    })

    token: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "description": "Health and readiness status of the service.",
    })

    status: str
