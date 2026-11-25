"""
Unit tests for how CachedRulesetsService maps cached tags to versions when there are several tag prefixes.
"""

import asyncio
from pathlib import Path

from csit_validation.services.cached_rulesets_service import CachedRulesetsService

CACHE_DIR = (Path(__file__).parent / "resources" / "github-cache").resolve()


def service(prefixes, ruleset_dir="dist/spectral") -> CachedRulesetsService:
    return CachedRulesetsService(lambda: str(CACHE_DIR), prefixes, ruleset_dir)


class TestVersionTagPrefixes:

    def test_default_prefix_ignores_other_prefixes(self):
        versions = service(["ruleset-"]).get_valid_version_tags

        assert "v1.4.0" not in versions
        assert versions["v1.1.0"] == "ruleset-v1.1.0"

    def test_earlier_prefix_wins_a_version_collision(self):
        versions = service(["ruleset-", "dev-ruleset-"]).get_valid_version_tags

        # ruleset-v1.1.0 and dev-ruleset-v1.1.0 both give v1.1.0; ruleset- is listed first.
        assert versions["v1.1.0"] == "ruleset-v1.1.0"
        # Only dev-ruleset-v1.4.0 gives v1.4.0.
        assert versions["v1.4.0"] == "dev-ruleset-v1.4.0"

    def test_prefix_order_decides_the_winner(self):
        versions = service(["dev-ruleset-", "ruleset-"]).get_valid_version_tags

        assert versions["v1.1.0"] == "dev-ruleset-v1.1.0"
        assert versions["v1.0.0"] == "ruleset-v1.0.0"

    def test_overlapping_prefixes_use_first_prefix_giving_a_valid_version(self, tmp_path):
        for tag in ["ruleset-v1.0.0", "ruleset-dev-v2.0.0"]:
            (tmp_path / "tags" / tag).mkdir(parents=True)

        svc = CachedRulesetsService(lambda: str(tmp_path), ["ruleset-", "ruleset-dev-"], "dist/spectral")

        # "ruleset-dev-v2.0.0" starts with "ruleset-", but "dev-v2.0.0" is not a version,
        # so the next prefix is tried.
        assert svc.get_valid_version_tags == {"v1.0.0": "ruleset-v1.0.0", "v2.0.0": "ruleset-dev-v2.0.0"}

    def test_rulesets_come_from_the_ruleset_directory(self):
        svc = service(["ruleset-", "dev-ruleset-"])

        rulesets = asyncio.run(svc.get_ruleset_files_in_tag("dev-ruleset-v1.1.0"))

        assert rulesets == {"dev-only-ruleset": "dist/spectral/dev-only-ruleset.yaml"}

    def test_trailing_slash_in_ruleset_directory_is_ignored(self):
        svc = service(["ruleset-"], ruleset_dir="dist/spectral/")

        rulesets = asyncio.run(svc.get_ruleset_files_in_tag("ruleset-v1.1.0"))

        assert rulesets["basic-ruleset"] == "dist/spectral/basic-ruleset.yaml"
