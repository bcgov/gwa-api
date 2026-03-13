#!/usr/bin/env bash
set -euo pipefail

# Configuration ────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/bcgov/csit-api-governance-spectral-style-guide.git"
CACHE_BASE_DIR="${1:-./tag-cache}"      
TAG_PREFIX="ruleset-"

# ──────────────────────────────────────────────────────────────────────────────

mkdir -p "$CACHE_BASE_DIR"
cd "$CACHE_BASE_DIR" || exit 1

# 1. Create a bare clone if it doesn't exist yet
BARE_REPO="bare.git"
if [ ! -d "$BARE_REPO" ]; then
    echo "Creating bare clone …"
    git clone --mirror "$REPO_URL" "$BARE_REPO"
fi

# 2. Enter bare repo and fetch latest tags
cd "$BARE_REPO" || exit 1
echo "Fetching latest tags …"
git fetch --tags --prune origin

# 3. Find all matching tags (sorted by version)
mapfile -t TAGS < <(git tag -l "${TAG_PREFIX}*" --sort=version:refname)

if [ ${#TAGS[@]} -eq 0 ]; then
    echo "No tags found matching '${TAG_PREFIX}*'"
    exit 1
fi

echo ""
echo "Found ${#TAGS[@]} tags matching '${TAG_PREFIX}*':"
printf '  - %s\n' "${TAGS[@]}"
echo ""

# 4. Create the structure and check out each tag as a worktree
cd .. || exit 1
mkdir -p tags

for tag in "${TAGS[@]}"; do
    target="tags/$tag"

    if [ -d "$target" ]; then
        echo "Already exists: $target → skipping"
        continue
    fi

    echo "Checking out $tag → $target"

    # Create worktree (detached HEAD)
    git -C "$BARE_REPO" worktree add --detach "../$target" "$tag"

    # Optional: show a quick summary
    (cd "$target" && git --no-pager log -1 --oneline --decorate)
    echo ""
done

# Optional: list all active worktrees
echo "All worktrees:"
git -C "$BARE_REPO" worktree list

echo ""
echo "Done."
echo "Cache structure created under: $(pwd)"
tree -L 2 2>/dev/null || ls -1 tags