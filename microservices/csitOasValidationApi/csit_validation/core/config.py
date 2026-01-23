from starlette.config import Config
import os
from pathlib import Path
from functools import lru_cache

# Config will be read from environment variables and/or ".env" files.
config = Config(env_file=".env" if os.path.exists(".env") else None)

# The VERSION_TAG_PREFIX environment variable will allow us to identify tags for specific environments
# e.g. dev-ruleset- for the dev environment, etc..
VERSION_TAG_PREFIX = config('VERSION_TAG_PREFIX', default="ruleset-")
RULESET_DIRECTORY = config('RULESET_DIRECTORY', default="spectral")
    
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
