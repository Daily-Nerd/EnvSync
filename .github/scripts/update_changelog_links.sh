#!/usr/bin/env bash
# Updates version comparison links in CHANGELOG.md

set -euo pipefail

VERSION="${1:-}"
PREV_VERSION="${2:-}"

if [ -z "$VERSION" ]; then
  echo "Usage: $0 <new-version> [previous-version]"
  exit 1
fi

CHANGELOG="CHANGELOG.md"
REPO_URL="https://github.com/Daily-Nerd/TripWire"

if [ ! -f "$CHANGELOG" ]; then
  echo "Error: CHANGELOG.md not found!"
  exit 1
fi

# If no previous version provided, try to detect it
if [ -z "$PREV_VERSION" ]; then
  PREV_VERSION=$(git describe --tags --abbrev=0 "v$VERSION^" 2>/dev/null | sed 's/^v//' || echo "")
fi

# Backup original
cp "$CHANGELOG" "$CHANGELOG.bak"

# Update [Unreleased] link to compare against new version
sed -i.tmp "s|\[Unreleased\]: .*|\[Unreleased\]: $REPO_URL/compare/v$VERSION...HEAD|" "$CHANGELOG"

# Check if version link already exists
if grep -q "^\[$VERSION\]: " "$CHANGELOG"; then
  echo "Version link for $VERSION already exists in CHANGELOG.md"
else
  if [ -n "$PREV_VERSION" ]; then
    # Add new version link after Unreleased
    sed -i.tmp "/^\[Unreleased\]: /a\\
[$VERSION]: $REPO_URL/compare/v$PREV_VERSION...v$VERSION" "$CHANGELOG"
  else
    # No previous version, create initial release link
    sed -i.tmp "/^\[Unreleased\]: /a\\
[$VERSION]: $REPO_URL/releases/tag/v$VERSION" "$CHANGELOG"
  fi
fi

# Clean up temp files
rm -f "$CHANGELOG.tmp" "$CHANGELOG.bak"

echo "✓ Updated CHANGELOG.md links for version $VERSION"
