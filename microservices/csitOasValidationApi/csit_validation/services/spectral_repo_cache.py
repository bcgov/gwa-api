import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Set
import logging
from csit_validation.util.log_decorator import log_entry_exit

logger = logging.getLogger(__name__)


class RWLock:
    """
    Simple readers-writer lock.
    Multiple readers allowed, writers exclusive.
    """

    @log_entry_exit(logger)
    def __init__(self):
        self._readers = 0
        self._writer = False
        self._cond = threading.Condition()

    @log_entry_exit(logger)
    def acquire_read(self):
        with self._cond:
            while self._writer:
                self._cond.wait()
            self._readers += 1

    @log_entry_exit(logger)
    def release_read(self):
        with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    @log_entry_exit(logger)
    def acquire_write(self):
        with self._cond:
            while self._writer or self._readers > 0:
                self._cond.wait()
            self._writer = True

    @log_entry_exit(logger)
    def release_write(self):
        with self._cond:
            self._writer = False
            self._cond.notify_all()


class SpectralRepoCache:
    """
    The Spectral Repo Cache maintains a local copy of each requested tag of the https://github.com/bcgov/csit-api-governance-spectral-style-guide
    repository. 

    When a call to get_cache_dir_for_tag is made, the service will checkout the tag from the repository if it does not already exist, and then return the path to the cache.
    If the tag has already been checked out by another request then the service will verify that the cache is up to date before returning the path.

    The service supports issuing locks for the tags so reading and writing to the cache can be synchronized.
    When updating the cache the service will obtain a write lock for the tag to prevent the cache from being modified during a validation request.
    When reading the cache for validation requests, the validation service will obtain a read lock for the tag.

    The service will also periodically update the cache to remove any tags that have been removed from the repository. 
    
    """

    @log_entry_exit(logger)
    def __init__(
        self,
        owner: str,
        repo: str,
        cache_root: Path,
        refresh_interval_seconds: int = 300,
    ):
        self.owner = owner
        self.repo = repo
        self.repo_url = f"https://github.com/{owner}/{repo}.git"

        self.cache_root = cache_root
        self.bare_repo_dir = cache_root / "repo.git"
        self.tags_dir = cache_root / "tags"

        self.refresh_interval = refresh_interval_seconds
        self._last_refresh_ts = 0.0

        self._global_lock = threading.RLock()
        self._tag_locks: Dict[str, RWLock] = {}

        # Lazy initialization flags
        self._bare_repo_initialized = False

        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.tags_dir.mkdir(parents=True, exist_ok=True)
        # Removed self._ensure_bare_repo() from here

    def _ensure_bare_repo(self):
        """Thread-safe lazy initialization of bare repo (called only when needed)."""
        with self._global_lock:
            if self._bare_repo_initialized:
                return
            if self.bare_repo_dir.exists():
                self._bare_repo_initialized = True
                return

            self._run_git(
                ["clone", "--bare", self.repo_url, str(self.bare_repo_dir)]
            )
            self._bare_repo_initialized = True

    # ============================================================
    # Public API
    # ============================================================

    @log_entry_exit(logger)
    def get_cache_dir_for_tag(self, tag: str) -> Path:
        """
        Returns the Path to the cached directory for the given tag.

        The caller should acquire a READ lock using get_tag_lock(tag) while
        using the returned directory.
        """
        self._refresh_if_needed()

        lock = self.get_tag_lock(tag)
        lock.acquire_write()
        try:
            tag_path = self.tags_dir / tag

            if tag_path.exists():
                return tag_path

            try:
                self._update_bare_repo()
                self._create_worktree_for_tag(tag)
            except Exception:
                # fallback to local cache if exists
                if tag_path.exists():
                    return tag_path
                raise

            return tag_path
        finally:
            lock.release_write()

    @log_entry_exit(logger)
    def get_tag_lock(self, tag: str) -> RWLock:
        """
        Returns the RWLock for a given tag.
        Use acquire_read() / release_read() around usage.
        """
        with self._global_lock:
            if tag not in self._tag_locks:
                self._tag_locks[tag] = RWLock()
            return self._tag_locks[tag]

    # ============================================================
    # Refresh logic
    # ============================================================

    @log_entry_exit(logger)
    def _refresh_if_needed(self):
        now = time.time()
        if now - self._last_refresh_ts < self.refresh_interval:
            return

        with self._global_lock:
            now = time.time()
            if now - self._last_refresh_ts < self.refresh_interval:
                return

            try:
                self._update_bare_repo()

                remote_tags = self._get_remote_tags()
                cached_tags = self._get_cached_tags()

                removed = cached_tags - remote_tags

                for tag in removed:
                    lock = self.get_tag_lock(tag)
                    lock.acquire_write()
                    try:
                        self._delete_cached_tag(tag)
                    finally:
                        lock.release_write()

            except Exception:
                # tolerate offline or git failures
                pass
            finally:
                self._last_refresh_ts = now

    # ============================================================
    # Git helpers (all now call _ensure_bare_repo() lazily)
    # ============================================================

    @log_entry_exit(logger)
    def _run_git(self, args, cwd=None):
        if cwd == self.bare_repo_dir and not self._bare_repo_initialized:
            self._ensure_bare_repo()
        subprocess.check_call(["git"] + args, cwd=cwd)

    @log_entry_exit(logger)
    def _update_bare_repo(self):
        self._ensure_bare_repo()  # Lazy init before fetch
        try:
            self._run_git(["fetch", "--tags", "origin"], cwd=self.bare_repo_dir)
        except Exception:
            pass

    @log_entry_exit(logger)
    def _create_worktree_for_tag(self, tag: str):
        self._ensure_bare_repo()  # Lazy init before worktree ops
        tag_dir = self.tags_dir / tag
        if tag_dir.exists():
            return

        # Validate tag exists
        subprocess.check_call(
            ["git", "rev-parse", f"refs/tags/{tag}"],
            cwd=self.bare_repo_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Create worktree
        self._run_git(
            ["worktree", "add", "--detach", str(tag_dir), tag],
            cwd=self.bare_repo_dir,
        )

        # Sparse checkout
        self._run_git(["sparse-checkout", "init", "--cone"], cwd=tag_dir)
        self._run_git(["sparse-checkout", "set", "spectral"], cwd=tag_dir)

    @log_entry_exit(logger)
    def _get_remote_tags(self) -> Set[str]:
        self._ensure_bare_repo()  # Lazy init before tag listing
        try:
            output = subprocess.check_output(
                ["git", "tag"], cwd=self.bare_repo_dir, text=True
            )
            return set(t.strip() for t in output.splitlines() if t.strip())
        except Exception:
            return set()

    @log_entry_exit(logger)
    def _get_cached_tags(self) -> Set[str]:
        return {p.name for p in self.tags_dir.iterdir() if p.is_dir()}

    @log_entry_exit(logger)
    def _delete_cached_tag(self, tag: str):
        self._ensure_bare_repo()  # Lazy init before worktree remove
        tag_dir = self.tags_dir / tag
        if not tag_dir.exists():
            return

        try:
            self._run_git(
                ["worktree", "remove", "--force", str(tag_dir)],
                cwd=self.bare_repo_dir,
            )
        except Exception:
            pass