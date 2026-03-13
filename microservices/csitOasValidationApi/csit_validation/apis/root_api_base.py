from typing import ClassVar, Tuple

from csit_validation.models.health import HealthResponse


class BaseRootApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseRootApi.subclasses = BaseRootApi.subclasses + (cls,)

    async def root(
        self,
    ) -> str:
        ...

    async def livez(
        self,
    ) -> str:
        ...

    async def readyz(
        self,
    ) -> str:
        ...

    async def health(
        self,
    ) -> HealthResponse:
        ...
