from starlette.config import Config
import os
import re
from pathlib import Path
from functools import lru_cache

# Config will be read from environment variables and/or ".env" files.
config = Config(env_file=".env" if os.path.exists(".env") else None)


def _split_list(value: str) -> list[str]:
    """Split a comma and/or whitespace separated setting into a list, dropping empty items."""
    return [item for item in re.split(r"[,\s]+", value) if item]


# The environment variables are described in README.md ("Ruleset versions").
RULESET_REPO_URL = config('RULESET_REPO_URL', default="https://github.com/bcgov/itk-api-governance.git")
VERSION_TAG_PREFIXES = config('VERSION_TAG_PREFIXES', cast=_split_list, default="ruleset-")  # ordered: earlier prefix wins
RULESET_DIRECTORY = config('RULESET_DIRECTORY', default="dist/spectral")
RULESET_FETCH_TIMEOUT_SECONDS = config('RULESET_FETCH_TIMEOUT_SECONDS', cast=int, default=45)

# ── Lazy computation for GITHUB_TAG_CACHE_PATH ───────────────────────────────

@lru_cache(maxsize=1)
def get_github_tag_cache_path() -> Path:
    """
    Lazily returns the cache path.
    - Reads the config only when first called
    - Uses default if not set
    - Result is cached for subsequent calls (performance + consistency)
    """

    return config('GITHUB_TAG_CACHE_PATH', default="csit-spectral-cache")


# Public name that can be used like before (but now lazy)
GITHUB_TAG_CACHE_PATH = get_github_tag_cache_path
