# csit_validation/impl/discovery_impl.py

import logging

from fastapi import HTTPException
from semver import Version

from csit_validation.apis.discovery_api_base import BaseDiscoveryApi
from csit_validation.models.version_list import VersionList
from csit_validation.models.ruleset_list import RulesetList
from csit_validation.services.github_ruleset_service import GitHubRulesetService
from csit_validation.core.config import (
    GITHUB_TOKEN,
    GITHUB_REPO_OWNER,
    GITHUB_REPO_NAME,
    RULESET_DIRECTORY,
    RULESET_FILE_EXTENSIONS,
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

        self.repo_owner = GITHUB_REPO_OWNER
        self.repo_name = GITHUB_REPO_NAME
        self.repo_token = GITHUB_TOKEN
        self.ruleset_dir = RULESET_DIRECTORY
        self.rules_file_extensions = RULESET_FILE_EXTENSIONS
        self.tag_prefix = "ruleset-"
        
        self.gh = GitHubRulesetService(
            self.repo_owner,
            self.repo_name,
            self.repo_token,
            self.ruleset_dir,
            self.rules_file_extensions,
        )

    async def list_versions(self) -> VersionList:
        """List all git tags that start with 'ruleset-' followed by a valid semantic version,
        returning only the version part (prefix removed) sorted newest first."""
        await self.gh.ensure_repo_exists()

        valid_tags = await self.gh.get_valid_version_tags()

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
        await self.gh.ensure_repo_exists()

        # Get the full prefixed tag name
        prefixed_tag = await self.gh.get_tag_from_version(version)
        logger.debug(f"Found prefixed tag: '{prefixed_tag}'")

        # If not found (get returns None), raise 404
        if prefixed_tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"Version '{version}' not found in {self.gh.repo_owner}/{self.gh.repo_name}"
            )

        # Fetch the actual ruleset files
        rulesets = await self.gh.get_ruleset_files_in_tag(prefixed_tag)

        # Return successful response (even if empty)
        return RulesetList(
            version=version,
            rulesets=sorted(rulesets.keys())
        )