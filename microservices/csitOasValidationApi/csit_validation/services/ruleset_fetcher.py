"""
Fetches the Spectral ruleset tags from the governance repository into the local tag cache.

entrypoint.sh runs this module before it starts the API:

    python -m csit_validation.services.ruleset_fetcher

Only tags that start with one of VERSION_TAG_PREFIXES are fetched. Each tag is unpacked into
<GITHUB_TAG_CACHE_PATH>/tags/<tag>/, and <GITHUB_TAG_CACHE_PATH>/manifest.json records the commit of
every tag, so the exact ruleset content behind each version can be traced.

If the fetch fails and the cache already holds tags from an earlier fetch (for example, when the
container restarts inside the same pod and the cache is an emptyDir), the earlier tags are kept and
the API starts. If the fetch fails and there is nothing cached, the process exits non-zero so the
container does not start without any rulesets.
"""

import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

TAGS_DIR_NAME = "tags"
MANIFEST_FILE_NAME = "manifest.json"
_STAGING_PREFIX = ".staging-"
_GLOB_CHARACTERS = set("*?[\\")


class RulesetFetchError(Exception):
    """Raised when the ruleset tags cannot be fetched."""

    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr


def _git_env() -> Dict[str, str]:
    env = dict(os.environ)
    # Never wait for credentials: the repository is public, and a prompt would hang the startup.
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _run_git(args: Sequence[str], timeout: float, cwd: Optional[Path] = None) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=_git_env(),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RulesetFetchError(f"git {args[0]} timed out after {timeout:.0f} seconds") from exc
    except OSError as exc:
        raise RulesetFetchError(f"Could not run git: {exc}") from exc

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RulesetFetchError(f"git {args[0]} failed (exit {result.returncode}): {stderr}", stderr=stderr)
    return result.stdout


def validate_prefixes(prefixes: Sequence[str]) -> List[str]:
    """Check that the prefixes can be used in a git refspec and as directory names."""
    if not prefixes:
        raise RulesetFetchError("VERSION_TAG_PREFIXES is empty; set at least one tag prefix")
    for prefix in prefixes:
        if any(char in _GLOB_CHARACTERS for char in prefix) or "/" in prefix or prefix.startswith("."):
            raise RulesetFetchError(
                f"Invalid tag prefix '{prefix}': use a plain prefix such as 'ruleset-', without wildcards or '/'"
            )
    return list(prefixes)


def read_manifest(cache_path: Path) -> Optional[dict]:
    """Return the manifest written by the last successful fetch, or None when there is none."""
    manifest_path = Path(cache_path) / MANIFEST_FILE_NAME
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        logger.warning(f"Could not read ruleset manifest {manifest_path}: {exc}")
        return None


def _list_fetched_tags(bare_repo: Path, timeout: float) -> Dict[str, str]:
    """Return {tag: commit} for the tags in the bare repository. Annotated tags are peeled to their commit."""
    output = _run_git(
        ["for-each-ref", "--format=%(refname:strip=2)%09%(objectname)%09%(*objectname)", "refs/tags"],
        timeout=timeout,
        cwd=bare_repo,
    ).decode("utf-8")

    tags: Dict[str, str] = {}
    for line in output.splitlines():
        name, object_id, peeled_id = (line.split("\t") + ["", ""])[:3]
        if not name:
            continue
        if "/" in name:
            logger.warning(f"Skipping tag '{name}': tag names containing '/' are not supported")
            continue
        tags[name] = peeled_id or object_id
    return tags


def _extract_commit(bare_repo: Path, commit: str, target: Path, timeout: float) -> None:
    archive = _run_git(["archive", "--format=tar", commit], timeout=timeout, cwd=bare_repo)
    target.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        tar.extractall(target, filter="data")


def fetch_ruleset_tags(
    repo_url: str,
    prefixes: Sequence[str],
    cache_path: Path,
    timeout: float,
) -> Dict[str, str]:
    """
    Fetch every tag that starts with one of the prefixes and replace the cached tags with them.

    Returns {tag: commit}. Raises RulesetFetchError if the fetch fails or finds no matching tags;
    in that case the existing cache is left as it was.
    """
    prefixes = validate_prefixes(prefixes)
    cache_path = Path(cache_path)
    cache_path.mkdir(parents=True, exist_ok=True)

    # Remove staging folders left behind by a fetch that was killed part way through.
    for leftover in cache_path.glob(f"{_STAGING_PREFIX}*"):
        shutil.rmtree(leftover, ignore_errors=True)

    # Build the new cache next to the old one, so a failed fetch never leaves a half-written cache
    # and the swap below is a rename on the same filesystem.
    staging = Path(tempfile.mkdtemp(prefix=_STAGING_PREFIX, dir=cache_path))
    try:
        bare_repo = staging / "repo.git"
        _run_git(["init", "--bare", "--quiet", str(bare_repo)], timeout=timeout)

        no_tags_message = f"No tags in {repo_url} start with any of: {', '.join(prefixes)}"
        refspecs = [f"+refs/tags/{prefix}*:refs/tags/{prefix}*" for prefix in prefixes]
        try:
            _run_git(
                ["fetch", "--quiet", "--no-tags", "--depth=1", repo_url, *refspecs],
                timeout=timeout,
                cwd=bare_repo,
            )
        except RulesetFetchError as exc:
            # A shallow fetch whose refspecs match no tags at all exits 1 without a message.
            if not exc.stderr:
                raise RulesetFetchError(no_tags_message) from exc
            raise

        tags = _list_fetched_tags(bare_repo, timeout)
        if not tags:
            raise RulesetFetchError(no_tags_message)

        new_tags_dir = staging / TAGS_DIR_NAME
        new_tags_dir.mkdir()
        for tag, commit in sorted(tags.items()):
            _extract_commit(bare_repo, commit, new_tags_dir / tag, timeout)

        manifest = {
            "repository": repo_url,
            "prefixes": prefixes,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "tags": dict(sorted(tags.items())),
        }

        # Swap the new tags in, then write the manifest that describes them.
        tags_dir = cache_path / TAGS_DIR_NAME
        old_tags_dir = staging / "old-tags"
        if tags_dir.exists():
            tags_dir.rename(old_tags_dir)
        new_tags_dir.rename(tags_dir)

        manifest_tmp = staging / MANIFEST_FILE_NAME
        manifest_tmp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        manifest_tmp.replace(cache_path / MANIFEST_FILE_NAME)

        return tags
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def run(
    repo_url: str,
    prefixes: Sequence[str],
    cache_path: Path,
    timeout: float,
) -> int:
    """Fetch the ruleset tags and return the process exit code (0 when the API can start)."""
    cache_path = Path(cache_path)
    logger.info(
        f"Fetching ruleset tags with prefixes {', '.join(prefixes) or '(none)'} from {repo_url} into {cache_path}"
    )
    try:
        tags = fetch_ruleset_tags(repo_url, prefixes, cache_path, timeout)
    except RulesetFetchError as exc:
        manifest = read_manifest(cache_path)
        cached_tags = (manifest or {}).get("tags") or {}
        if cached_tags and (cache_path / TAGS_DIR_NAME).is_dir():
            logger.warning(
                f"Ruleset fetch failed: {exc}. Serving the {len(cached_tags)} tags fetched earlier "
                f"at {manifest.get('fetched_at', 'an unknown time')}."
            )
            for tag, commit in cached_tags.items():
                logger.info(f"Ruleset tag {tag} at commit {commit} (cached)")
            return 0
        logger.exception(f"Ruleset fetch failed and no rulesets are cached: {exc}")
        return 1

    logger.info(f"Fetched {len(tags)} ruleset tags")
    for tag, commit in sorted(tags.items()):
        logger.info(f"Ruleset tag {tag} at commit {commit}")
    return 0


def main() -> int:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level_name if level_name in logging.getLevelNamesMapping() else "INFO",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from csit_validation.core.config import (
        GITHUB_TAG_CACHE_PATH,
        RULESET_FETCH_TIMEOUT_SECONDS,
        RULESET_REPO_URL,
        VERSION_TAG_PREFIXES,
    )

    return run(
        repo_url=RULESET_REPO_URL,
        prefixes=VERSION_TAG_PREFIXES,
        cache_path=Path(GITHUB_TAG_CACHE_PATH()),
        timeout=RULESET_FETCH_TIMEOUT_SECONDS,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
