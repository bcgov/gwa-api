"""
Unit tests for the startup ruleset fetcher.

Each test builds a small git repository with tags in a temporary directory and fetches from it
over file://, so no network access is needed.
"""

import json
import logging
import os
import subprocess
from pathlib import Path

import pytest

import csit_validation.core.config as config
from csit_validation.services import ruleset_fetcher
from csit_validation.services.ruleset_fetcher import (
    RulesetFetchError,
    fetch_ruleset_tags,
    read_manifest,
    run,
    validate_prefixes,
)

TIMEOUT = 30


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch):
    """Keep the developer's git configuration (signing, URL rewrites, ...) out of the tests."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def commit_file(repo: Path, relative_path: str, content: str, message: str) -> str:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    git(repo, "add", relative_path)
    git(repo, "commit", "--quiet", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def source_repo(tmp_path):
    """
    A repository with:
      ruleset-v1.0.0          lightweight tag on commit 1
      dev-ruleset-v1.1.0      annotated tag on commit 2
      other-v9.9.9            tag that no test prefix matches
      ruleset-nested/v2.0.0   tag containing '/', which is skipped
    """
    repo = tmp_path / "source"
    repo.mkdir()
    git(repo, "init", "--quiet")
    commit_1 = commit_file(repo, "dist/spectral/basic-ruleset.yaml", "rules: {}  # v1\n", "v1")
    git(repo, "tag", "ruleset-v1.0.0")
    commit_2 = commit_file(repo, "dist/spectral/basic-ruleset.yaml", "rules: {}  # v2\n", "v2")
    git(repo, "tag", "-a", "-m", "dev release", "dev-ruleset-v1.1.0")
    git(repo, "tag", "other-v9.9.9")
    git(repo, "tag", "ruleset-nested/v2.0.0")
    return {"url": f"file://{repo}", "path": repo, "commit_1": commit_1, "commit_2": commit_2}


@pytest.fixture
def cache_path(tmp_path):
    return tmp_path / "cache"


class TestFetchRulesetTags:

    def test_fetches_tags_matching_the_prefixes(self, source_repo, cache_path):
        tags = fetch_ruleset_tags(source_repo["url"], ["ruleset-", "dev-ruleset-"], cache_path, TIMEOUT)

        # Annotated tags are recorded with the commit they point to, not the tag object.
        assert tags == {
            "ruleset-v1.0.0": source_repo["commit_1"],
            "dev-ruleset-v1.1.0": source_repo["commit_2"],
        }

        tags_dir = cache_path / "tags"
        assert sorted(entry.name for entry in tags_dir.iterdir()) == ["dev-ruleset-v1.1.0", "ruleset-v1.0.0"]
        assert (tags_dir / "ruleset-v1.0.0" / "dist/spectral/basic-ruleset.yaml").read_text() == "rules: {}  # v1\n"
        assert (tags_dir / "dev-ruleset-v1.1.0" / "dist/spectral/basic-ruleset.yaml").read_text() == "rules: {}  # v2\n"

        # Plain file trees: no git metadata and no staging folders left behind.
        assert not (tags_dir / "ruleset-v1.0.0" / ".git").exists()
        assert sorted(entry.name for entry in cache_path.iterdir()) == ["manifest.json", "tags"]

    def test_writes_manifest(self, source_repo, cache_path):
        fetch_ruleset_tags(source_repo["url"], ["ruleset-", "dev-ruleset-"], cache_path, TIMEOUT)

        manifest = json.loads((cache_path / "manifest.json").read_text())
        assert manifest["repository"] == source_repo["url"]
        assert manifest["prefixes"] == ["ruleset-", "dev-ruleset-"]
        assert manifest["fetched_at"].endswith("Z")
        assert manifest["tags"] == {
            "dev-ruleset-v1.1.0": source_repo["commit_2"],
            "ruleset-v1.0.0": source_repo["commit_1"],
        }
        assert read_manifest(cache_path) == manifest

    def test_refetch_replaces_previous_tags(self, source_repo, cache_path):
        fetch_ruleset_tags(source_repo["url"], ["ruleset-", "dev-ruleset-"], cache_path, TIMEOUT)
        tags = fetch_ruleset_tags(source_repo["url"], ["dev-ruleset-"], cache_path, TIMEOUT)

        assert list(tags) == ["dev-ruleset-v1.1.0"]
        assert [entry.name for entry in (cache_path / "tags").iterdir()] == ["dev-ruleset-v1.1.0"]
        assert read_manifest(cache_path)["tags"] == {"dev-ruleset-v1.1.0": source_repo["commit_2"]}

    def test_no_matching_tags_raises_and_keeps_cache(self, source_repo, cache_path):
        fetch_ruleset_tags(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT)

        with pytest.raises(RulesetFetchError, match="No tags"):
            fetch_ruleset_tags(source_repo["url"], ["missing-"], cache_path, TIMEOUT)

        assert [entry.name for entry in (cache_path / "tags").iterdir()] == ["ruleset-v1.0.0"]
        assert list(read_manifest(cache_path)["tags"]) == ["ruleset-v1.0.0"]

    def test_only_unsupported_tags_raises(self, source_repo, cache_path):
        # "ruleset-n" matches only ruleset-nested/v2.0.0, which is skipped.
        with pytest.raises(RulesetFetchError, match="No tags"):
            fetch_ruleset_tags(source_repo["url"], ["ruleset-n"], cache_path, TIMEOUT)

    def test_unreachable_repository_raises(self, tmp_path, cache_path):
        with pytest.raises(RulesetFetchError, match="git fetch failed"):
            fetch_ruleset_tags(f"file://{tmp_path / 'missing'}", ["ruleset-"], cache_path, TIMEOUT)

    def test_removes_leftover_staging_folders(self, source_repo, cache_path):
        leftover = cache_path / ".staging-killed"
        leftover.mkdir(parents=True)
        (leftover / "partial").write_text("x")

        fetch_ruleset_tags(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT)

        assert not leftover.exists()


class TestInterruptedSwap:

    def test_killed_after_previous_tags_moved_aside_restores_them(self, source_repo, tmp_path, cache_path):
        run(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT)
        # State left by a process killed between moving tags/ aside and moving the new tree in.
        (cache_path / "tags").rename(cache_path / ".previous-tags")

        assert run(f"file://{tmp_path / 'missing'}", ["ruleset-"], cache_path, TIMEOUT) == 0

        assert (cache_path / "tags" / "ruleset-v1.0.0" / "dist/spectral/basic-ruleset.yaml").is_file()
        assert not (cache_path / ".previous-tags").exists()

    def test_leftover_previous_tags_is_deleted_when_new_tags_are_in_place(self, source_repo, cache_path):
        run(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT)
        (cache_path / ".previous-tags" / "stale").mkdir(parents=True)

        assert run(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT) == 0

        assert not (cache_path / ".previous-tags").exists()
        assert [entry.name for entry in (cache_path / "tags").iterdir()] == ["ruleset-v1.0.0"]

    def test_failed_swap_keeps_previous_tags_and_manifest(self, source_repo, cache_path, monkeypatch):
        run(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT)
        manifest_before = read_manifest(cache_path)

        real_replace = Path.replace

        def failing_replace(self, target):
            if Path(target).name == "manifest.json":
                raise OSError("disk full")
            return real_replace(self, target)

        monkeypatch.setattr(Path, "replace", failing_replace)

        with pytest.raises(RulesetFetchError, match="disk full"):
            fetch_ruleset_tags(source_repo["url"], ["ruleset-", "dev-ruleset-"], cache_path, TIMEOUT)

        assert [entry.name for entry in (cache_path / "tags").iterdir()] == ["ruleset-v1.0.0"]
        assert read_manifest(cache_path) == manifest_before
        assert not (cache_path / ".previous-tags").exists()


class TestValidatePrefixes:

    def test_accepts_plain_prefixes(self):
        assert validate_prefixes(["ruleset-", "dev-ruleset-"]) == ["ruleset-", "dev-ruleset-"]

    @pytest.mark.parametrize("prefixes", [[], ["ruleset-*"], ["rule?"], ["a/b"], [".hidden"]])
    def test_rejects_invalid_prefixes(self, prefixes):
        with pytest.raises(RulesetFetchError):
            validate_prefixes(prefixes)


class TestRunGit:

    def test_timeout_raises_fetch_error(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git", timeout=1)

        monkeypatch.setattr(ruleset_fetcher.subprocess, "run", fake_run)
        with pytest.raises(RulesetFetchError, match="timed out"):
            ruleset_fetcher._run_git(["fetch"], timeout=1)

    def test_missing_git_raises_fetch_error(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise FileNotFoundError("git")

        monkeypatch.setattr(ruleset_fetcher.subprocess, "run", fake_run)
        with pytest.raises(RulesetFetchError, match="Could not run git"):
            ruleset_fetcher._run_git(["fetch"], timeout=1)


class TestRun:

    def test_success_returns_zero_and_logs_commits(self, source_repo, cache_path, caplog):
        caplog.set_level(logging.INFO, logger=ruleset_fetcher.__name__)

        assert run(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT) == 0
        assert f"Ruleset tag ruleset-v1.0.0 at commit {source_repo['commit_1']}" in caplog.text

    def test_failure_without_cache_returns_one(self, tmp_path, cache_path, caplog):
        assert run(f"file://{tmp_path / 'missing'}", ["ruleset-"], cache_path, TIMEOUT) == 1
        assert "no rulesets are cached" in caplog.text

    def test_failure_with_cache_keeps_earlier_tags(self, source_repo, tmp_path, cache_path, caplog):
        caplog.set_level(logging.INFO, logger=ruleset_fetcher.__name__)
        assert run(source_repo["url"], ["ruleset-"], cache_path, TIMEOUT) == 0

        assert run(f"file://{tmp_path / 'missing'}", ["ruleset-"], cache_path, TIMEOUT) == 0
        assert "Serving the 1 tags fetched earlier" in caplog.text
        assert f"Ruleset tag ruleset-v1.0.0 at commit {source_repo['commit_1']} (cached)" in caplog.text
        assert (cache_path / "tags" / "ruleset-v1.0.0" / "dist/spectral/basic-ruleset.yaml").is_file()

    def test_invalid_prefix_without_cache_returns_one(self, source_repo, cache_path):
        assert run(source_repo["url"], ["ruleset-*"], cache_path, TIMEOUT) == 1


class TestMain:

    def test_main_uses_configuration(self, source_repo, cache_path, monkeypatch):
        monkeypatch.setattr(config, "RULESET_REPO_URL", source_repo["url"])
        monkeypatch.setattr(config, "VERSION_TAG_PREFIXES", ["dev-ruleset-"])
        monkeypatch.setattr(config, "RULESET_FETCH_TIMEOUT_SECONDS", TIMEOUT)
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_path))
        monkeypatch.setenv("LOG_LEVEL", "NOT-A-LEVEL")
        config.get_github_tag_cache_path.cache_clear()
        try:
            assert ruleset_fetcher.main() == 0
        finally:
            config.get_github_tag_cache_path.cache_clear()

        assert list(read_manifest(cache_path)["tags"]) == ["dev-ruleset-v1.1.0"]


class TestReadManifest:

    def test_missing_manifest_returns_none(self, cache_path):
        assert read_manifest(cache_path) is None

    def test_unreadable_manifest_returns_none(self, cache_path):
        cache_path.mkdir()
        (cache_path / "manifest.json").write_text("not json")
        assert read_manifest(cache_path) is None


class TestSplitList:

    def test_splits_on_commas_and_whitespace(self):
        assert config._split_list("ruleset-, dev-ruleset-\n other-") == ["ruleset-", "dev-ruleset-", "other-"]

    def test_empty_value_gives_empty_list(self):
        assert config._split_list(" , ") == []
