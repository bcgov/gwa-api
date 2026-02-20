# csit_validation/impl/discovery_impl.py

import logging

from fastapi import HTTPException
from semver import Version
from pathlib import Path

from csit_validation.apis.discovery_api_base import BaseDiscoveryApi
from csit_validation.models.version_list import VersionList
from csit_validation.models.ruleset_list import RulesetList
from csit_validation.services.cached_rulesets_service import CachedRulesetsService
from csit_validation.core.config import (
    GITHUB_TAG_CACHE_PATH,
    VERSION_TAG_PREFIX,
    RULESET_DIRECTORY,
)

logger = logging.getLogger(__name__)


class DiscoveryApiImpl(BaseDiscoveryApi):
    """
    The Discovery API endpoints support the listing of published versions of the CSIT API Governance Rules
    and the rulesets available in each version.

    The primary purpose of these endpoints is to allow the versions and rulesets to be discovered so they can be
    used as parameters to the OAS Validaton requests implemented by the Validation API.

    See the GitHubRulesetService for details on how the versions and rules sets are discovered. 
    """

    def __init__(self):

        self.github_tag_cache_path = GITHUB_TAG_CACHE_PATH
        self.version_tag_prefix = VERSION_TAG_PREFIX
        self.ruleset_dir = RULESET_DIRECTORY
        self.tag_prefix = "ruleset-"
        
        self.gh = CachedRulesetsService(
            self.github_tag_cache_path,
            self.version_tag_prefix,
            self.ruleset_dir,
        )

    async def list_versions(self) -> VersionList:
        """List all git tags that start with 'ruleset-' followed by a valid semantic version,
        returning only the version part (prefix removed) sorted newest first."""

        valid_tags = self.gh.get_valid_version_tags

        # Sort descending by semantic version (parse without prefix)
        sorted_tags = sorted(
            valid_tags.keys(),
            key=self.parse_semver,
            reverse=True  # newest first
        )

        return VersionList(versions=sorted_tags)

    def parse_semver(self, tag: str) -> Version:
        """Strip common 'v' prefix and parse safely."""
        clean = tag.lstrip('v')  # removes leading v/V if present
        return Version.parse(clean)

    async def list_rulesets_in_version(
        self,
        version: str
    ) -> RulesetList:
        """List all ruleset files available under the given version/tag."""

        # Get the full prefixed tag name
        version_to_tag_map = self.gh.get_valid_version_tags
        prefixed_tag = version_to_tag_map.get(version)
        logger.debug(f"Found prefixed tag: '{prefixed_tag}'")

        # If not found (get returns None), raise 404
        if prefixed_tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"Version '{version}' not found"
            )

        # Fetch the actual ruleset files
        rulesets = await self.gh.get_ruleset_files_in_tag(prefixed_tag)

        file_paths = list(rulesets.keys())

        sorted_paths = sorted(
            file_paths,
            key=lambda p: (Path(p).parent.as_posix() or '', Path(p).name)
        )

        # Return successful response (even if empty)
        return RulesetList(
            version=version,
            rulesets=sorted_paths
        )