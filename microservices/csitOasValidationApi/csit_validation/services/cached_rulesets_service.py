import re
import logging
from pathlib import Path
from functools import cached_property
from typing import Callable, Dict, Optional, Sequence, Tuple
from csit_validation.util.log_decorator import log_entry_exit

logger = logging.getLogger(__name__)

SEMVER_PATTERN = re.compile(r'^v\d+\.\d+\.\d+(-[\w\-.]+)?$')


class CachedRulesetsService:
    """
    The CachedRulesetsService is a utility class that retrieves published versions of the API Governance rules
    and the rulesets available in each version from a local cache of the rules repository's tags.

    The rules are maintained in the https://github.com/bcgov/itk-api-governance repository and the versions are
    identified by tags in the repository. ruleset_fetcher fetches the tags into the cache when the service starts.

    The service determines the versions by listing the cached tags and keeping the tags that start with one of the
    configured prefixes followed by a valid semantic version (v<semver>). The version is the tag with its prefix
    removed.

    With the prefixes ["ruleset-"], example tags that will be identified as versions are:
        ruleset-v1.0.0      → v1.0.0
        ruleset-v1.2.3      → v1.2.3
        ruleset-v1.3.0-Beta1 → v1.3.0-Beta1

    Tags that don't start with a prefix or don't follow semantic versioning are ignored. For example:
        ruleset-junk-tag
        junk-tag

    The prefixes are ordered. When two tags give the same version, the tag whose prefix comes first wins.
    With the prefixes ["ruleset-", "dev-ruleset-"] and the tags ruleset-v1.1.0, dev-ruleset-v1.1.0 and
    dev-ruleset-v1.2.0:
        v1.1.0 → ruleset-v1.1.0      (ruleset- is listed before dev-ruleset-)
        v1.2.0 → dev-ruleset-v1.2.0  (no ruleset-v1.2.0 tag exists)

    Rulesets in each version are the yaml or yml files within the ruleset directory (dist/spectral by default),
    relative to the root of the tag. For example:
        dist/spectral/basic-ruleset.yaml → basic-ruleset
        dist/spectral/sdx/ruleset.yml    → sdx/ruleset
    """

    def __init__(
            self,
            github_tag_cache_path: Callable[[], str],
            version_tag_prefixes: Sequence[str],
            ruleset_dir: str,
    ):

        self.github_tag_cache_path = github_tag_cache_path
        self.version_tag_prefixes = list(version_tag_prefixes)
        self.ruleset_dir = ruleset_dir.strip("/")
        self.rules_file_extensions = [".yml", ".yaml"]

        self._ruleset_files_cache: Dict[str, Dict[str, str]] = {}

    def _version_for_tag(self, tag_name: str) -> Optional[Tuple[int, str]]:
        """Return (prefix priority, version) for the first prefix that gives a valid version, or None."""
        for priority, prefix in enumerate(self.version_tag_prefixes):
            if not tag_name.startswith(prefix):
                continue
            version_part = tag_name[len(prefix):]
            if SEMVER_PATTERN.match(version_part):
                return priority, version_part
        return None

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
        return self.scan_version_tags()

    def scan_version_tags(self) -> Dict[str, str]:
        """
        Returns map: version → full tag name, read from the cache on every call.

        Not decorated with log_entry_exit and logs only at DEBUG, so the readiness probe and the
        health check can call it on every request without filling the log.
        """
        tag_dir = Path(self.github_tag_cache_path()) / "tags"
        if not tag_dir.is_dir():
            return {}

        # version → (prefix priority, tag name)
        selected: Dict[str, Tuple[int, str]] = {}

        for entry in sorted(tag_dir.iterdir()):
            if not entry.is_dir():
                continue

            tag_name = entry.name
            match = self._version_for_tag(tag_name)
            if match is None:
                continue
            priority, version_part = match

            current = selected.get(version_part)
            if current is None or priority < current[0]:
                if current is not None:
                    logger.debug(f"Version {version_part}: tag {tag_name} takes precedence over {current[1]}")
                selected[version_part] = (priority, tag_name)
            else:
                logger.debug(f"Version {version_part}: tag {current[1]} takes precedence over {tag_name}")

        return {version_part: tag_name for version_part, (_, tag_name) in selected.items()}

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