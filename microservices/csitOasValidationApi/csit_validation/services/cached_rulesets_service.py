import re
import logging
from pathlib import Path
from functools import cached_property
from typing import  Optional, Tuple, Dict
from csit_validation.util.log_decorator import log_entry_exit

logger = logging.getLogger(__name__)


class CachedRulesetsService:
    """
    The CachedRulesetsService is a utility class that retrieves published versions of the CSIT API Governance Rules
    and the rulesets available in each version from a cached version of the CSIT API Governance Rules Git repository.

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

    @log_entry_exit(logger)
    def __init__(
            self,
            github_tag_cache_path: Path,
            version_tag_prefix: str,
            ruleset_dir: str,
    ):

        self.github_tag_cache_path = github_tag_cache_path
        self.version_tag_prefix = version_tag_prefix
        self.ruleset_dir = ruleset_dir
        self.rules_file_extensions = [".yml", ".yaml"]

        self._ruleset_files_cache: Dict[str, Dict[str, str]] = {}

    @cached_property
    @log_entry_exit(logger)
    def get_valid_version_tags(self) -> Dict[str, str]:
        """
        Returns map: version → full tag name
        Discovers tags from local filesystem cache only once (cached_property)
        """
        tag_dir = Path(self.github_tag_cache_path()) / "tags"
        
        if not tag_dir.is_dir():
            logger.warning(f"Tag cache directory not found: {tag_dir}")
            return {}

        version_to_tag_map: Dict[str, str] = {}
        semver_pattern = re.compile(r'^v\d+\.\d+\.\d+(-[\w\-.]+)?$')

        # Look for all directories that could represent tags
        for entry in tag_dir.iterdir():
            if not entry.is_dir():
                continue
                
            tag_name = entry.name
            
            # Skip tags that don't match the expected prefix
            if not tag_name.startswith(self.version_tag_prefix):
                continue

            version_part = tag_name[len(self.version_tag_prefix):]
            
            # Validate semantic version pattern
            if not semver_pattern.match(version_part):
                continue

            # If we got here → valid version tag
            version_to_tag_map[version_part] = tag_name

        return version_to_tag_map

    @log_entry_exit(logger)
    async def get_ruleset_files_in_tag(self, tag: str) -> Dict[str, str]:
        """
        Return map of ruleset identifier → full path
        Key = filename without extension (e.g. "basic-ruleset")
        """
        if tag in self._ruleset_files_cache:
            return self._ruleset_files_cache[tag]
    
        tag_dir = Path(self.github_tag_cache_path()) / "tags" / tag

        if not tag_dir.is_dir():
            logger.warning(f"Tag directory not found in cache: {tag_dir}")
            return {}

        ruleset_files_map: Dict[str, str] = {}
        prefix_len = len(self.ruleset_dir) + 1  # +1 for '/'

        # Find all matching files recursively
        for file_path in tag_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Get path relative to the tag root 
            relative_to_tag = file_path.relative_to(tag_dir).as_posix()

            if (
                relative_to_tag.startswith(f"{self.ruleset_dir}/")
                and any(relative_to_tag.lower().endswith(ext.strip()) for ext in self.rules_file_extensions)
            ):
                relative_path = relative_to_tag[prefix_len:]
                last_dot = relative_path.rfind('.')
                key = relative_path[:last_dot] if last_dot != -1 else relative_path
                # Keep the original repo-style path (not filesystem absolute)
                ruleset_files_map[key] = relative_to_tag

        logger.debug(f"Found {len(ruleset_files_map)} ruleset files in tag {tag}")
        self._ruleset_files_cache[tag] = ruleset_files_map
        return ruleset_files_map

    @log_entry_exit(logger)
    async def get_ruleset_tuple(self, tag: str, ruleset: str) -> Optional[Tuple[str, str]]:
        """Returns (ruleset_name, full_path_in_repo) or None"""

        rulesets = await self.get_ruleset_files_in_tag(tag)
        if ruleset in rulesets:
            return (ruleset, rulesets[ruleset])

        return None