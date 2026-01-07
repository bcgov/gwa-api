from starlette.config import Config
import os
import logging
import tempfile
from pathlib import Path
from functools import lru_cache

_logger = logging.getLogger(__name__)

# Config will be read from environment variables and/or ".env" files.
config = Config(env_file=".env" if os.path.exists(".env") else None)

GITHUB_REPO_OWNER = config('GITHUB_REPO_OWNER', default='bcgov') 
GITHUB_REPO_NAME = config('GITHUB_REPO_NAME', default='csit-api-governance-spectral-style-guide')  
GITHUB_TOKEN = config('GITHUB_TOKEN', default=None)  

if not GITHUB_TOKEN:
    _logger.warning(
            "GITHUB_TOKEN not provided. This may cause 503 Service Unavailable "
            "and performance issues due to GitHub rate limiting even when "
            "the repository is public."
        )
    
RULESET_DIRECTORY = config('RULESET_DIRECTORY', default="spectral")
RULESET_FILE_EXTENSIONS = config('RULESET_FILE_EXTENSIONS', default=".yml,.yaml").split(",")
    
# ── Lazy computation for GITHUB_TAG_CACHE_PATH ───────────────────────────────

@lru_cache(maxsize=1)
def get_github_tag_cache_path() -> Path:
    """
    Lazily computes and returns the cache path.
    - Reads the config only when first called
    - Uses tempfile fallback if not set
    - Result is cached for subsequent calls (performance + consistency)
    """
    cache_dir_str = config('GITHUB_TAG_CACHE_PATH', default=None)
    if cache_dir_str:
        path = Path(cache_dir_str)
    else:
        path = Path(tempfile.gettempdir()) / "csit-spectral-cache"
    
    # Optional: ensure the directory exists when first accessed
    path.mkdir(parents=True, exist_ok=True)
    
    return path


# Public name that can be used like before (but now lazy)
GITHUB_TAG_CACHE_PATH = get_github_tag_cache_path