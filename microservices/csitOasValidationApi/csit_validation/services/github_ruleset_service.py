import re
import httpx
from typing import  Optional, Tuple
from fastapi import HTTPException
import logging
from csit_validation.util.log_decorator import log_entry_exit

logger = logging.getLogger(__name__)


class GitHubRulesetService:
    """
    The GitHubRulesetService is a utility class that encapsulates HTTPS requests to the configured GitHub
    repository to support retrieving the published versions of the CSIT API Governance Rules
    and the rulesets available in each version.

    The CSIT API Governance Rules are maintained in the https://github.com/bcgov/csit-api-governance-spectral-style-guide
    repository and the versions are identified by commit tags in the repository.  

    The service determines the versions by obtaining a list of the repositories tags and filtering for tags that follow the format
    ruleset-v<semver> where <semver> is a valid semantic verions.  

    Example tags that will be identified as versions are:
        ruleset-v1.0.0
        ruleset-v1.2.3
        ruleset-v1.3.0-Beta1
        ruleset-v1.1.0

    Tags that are not prefixed with 'ruleset-' or do not follow semantic versions will be ignored.  For example:
        ruleset-junk-tag
        junk-tag

        
    Rulesets in each version are identified as yaml or yaml files within the 'spectral' directory in the root of the repository.
    
    For example:
        spectral/basic-ruleset.yaml
        spectral/sdx/ruleset.yml
    """

    _TAG_PREFIX = "ruleset-"

    @log_entry_exit(logger)
    def __init__(
            self,
            owner: str,
            repo: str,
            token:str,
            ruleset_dir: str,
            rules_file_extensions: str,
    ):

        self.repo_owner = owner
        self.repo_name = repo
        self.repo_token = token
        self.ruleset_dir = ruleset_dir
        self.rules_file_extensions = rules_file_extensions
        self.tag_prefix = "ruleset-"

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "csit-validation-api/1.0",
        }

        if self.repo_token:
            headers["Authorization"] = f"token {self.repo_token}"

        self.http_client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=20.0
        )

    @log_entry_exit(logger)
    async def ensure_repo_exists(self):
        """Check if the configured repo exists. Raises 500 if not."""

        try:
            resp = await self.http_client.get(f"/repos/{self.repo_owner}/{self.repo_name}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 404):
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Internal server error: The configured GitHub repository "
                        f"{self.repo_owner}/{self.repo_name} does not exist or is inaccessible."
                    )
                )
            if e.response.status_code == 429:
                raise HTTPException(
                    status_code=503,
                    detail="GitHub API rate limit exceeded."
                )
            raise HTTPException(
                status_code=502,
                detail=f"Failed to verify repository: {e.response.status_code} - {e.response.text[:200]}"
            )

    @log_entry_exit(logger)
    async def get_valid_version_tags(self) -> dict[str, str]:
        """Fetch all tags and return map: version → full tag name"""

        response = await self.http_client.get(
            f"/repos/{self.repo_owner}/{self.repo_name}/tags",
            params={"per_page": 100}
        )
        response.raise_for_status()
        all_tags = response.json()

        version_to_tag_map: dict[str, str] = {}
        semver_pattern = re.compile(r'^v\d+\.\d+\.\d+(-[\w\-.]+)?$')

        for tag in all_tags:
            tag_name = tag["name"]
            if not tag_name.startswith(self._TAG_PREFIX):
                continue

            version_part = tag_name[len(self._TAG_PREFIX):]
            if not semver_pattern.match(version_part):
                continue

            version_to_tag_map[version_part] = tag_name

        return version_to_tag_map

    @log_entry_exit(logger)
    async def get_tag_from_version(self, version: str) -> Optional[str]:
        """Retrieve the full tag name (with prefix) for a given version part."""

        version_to_tag_map = await self.get_valid_version_tags()

        return version_to_tag_map.get(version)

    @log_entry_exit(logger)
    async def get_ruleset_files_in_tag(self, tag: str) -> dict[str, str]:
        """
        Return map of ruleset identifier → full path in repo
        Key = filename without extension (e.g. "basic-ruleset")
        """

        url = f"/repos/{self.repo_owner}/{self.repo_name}/git/trees/{tag}?recursive=1"
        resp = await self.http_client.get(url)
        resp.raise_for_status()

        tree = resp.json().get("tree", [])
        ruleset_files_map: dict[str, str] = {}

        prefix_len = len(self.ruleset_dir) + 1  # +1 for '/'

        for item in tree:
            path = item["path"]
            if (
                item["type"] == "blob"
                and path.startswith(f"{self.ruleset_dir}/")
                and any(path.lower().endswith(ext.strip()) for ext in self.rules_file_extensions)
            ):
                relative_path = path[prefix_len:]
                last_dot = relative_path.rfind('.')
                key = relative_path[:last_dot] if last_dot != -1 else relative_path
                ruleset_files_map[key] = path

        return ruleset_files_map

    @log_entry_exit(logger)
    async def get_ruleset_tuple(self, tag: str, ruleset: str) -> Optional[Tuple[str, str]]:
        """Returns (ruleset_name, full_path_in_repo) or None"""

        rulesets = await self.get_ruleset_files_in_tag(tag)
        if ruleset in rulesets:
            return (ruleset, rulesets[ruleset])

        return None