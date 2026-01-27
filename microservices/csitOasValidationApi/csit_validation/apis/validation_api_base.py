from typing import ClassVar, Tuple

from csit_validation.models.validation_response import ValidationResponse
from fastapi import Request

class BaseValidationApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseValidationApi.subclasses = BaseValidationApi.subclasses + (cls,)
    async def create_validation(
        self,
        version: str,
        ruleset: str,
        request: Request
    ) -> ValidationResponse:
        ...
