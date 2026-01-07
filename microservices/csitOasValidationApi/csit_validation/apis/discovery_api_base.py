from typing import ClassVar, Tuple

from csit_validation.models.ruleset_list import RulesetList
from csit_validation.models.version_list import VersionList


class BaseDiscoveryApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseDiscoveryApi.subclasses = BaseDiscoveryApi.subclasses + (cls,)
    async def list_versions(
        self,
    ) -> VersionList:
        ...


    async def list_rulesets_in_version(
        self,
        version: str,
    ) -> RulesetList:
        ...
