#!/usr/bin/env bash
# Validates CHANGELOG.md is properly updated for the release version

set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

CHANGELOG="CHANGELOG.md"

if [ ! -f "$CHANGELOG" ]; then
  echo "::error::CHANGELOG.md not found!"
  exit 1
fi

# Check if version exists in CHANGELOG
if ! grep -q "## \[$VERSION\]" "$CHANGELOG"; then
  echo "::error::Version [$VERSION] not found in CHANGELOG.md"
  echo "Please add a changelog entry for version $VERSION before releasing."
  echo ""
  echo "Expected format:"
  echo "## [$VERSION] - $(date +%Y-%m-%d)"
  echo ""
  echo "### Added"
  echo "- New feature description"
  exit 1
fi

# Check if version has content (not just the header)
# Extract lines between this version header and the next version header (or EOF)
SECTION_CONTENT=$(awk "/## \[$VERSION\]/{flag=1; next} /## \[/{flag=0} flag" "$CHANGELOG" | grep -v "^$" | grep -v "^#" || true)
if [ -z "$SECTION_CONTENT" ]; then
  echo "::error::Version [$VERSION] in CHANGELOG.md has no content!"
  echo "Please add meaningful changelog entries before releasing."
  exit 1
fi

# Check if version link exists at bottom
if ! grep -q "\[$VERSION\]:" "$CHANGELOG"; then
  echo "::warning::Version comparison link [$VERSION]: missing at bottom of CHANGELOG.md"
  echo "Expected format:"
  echo "[$VERSION]: https://github.com/Daily-Nerd/TripWire/compare/vX.Y.Z...v$VERSION"
fi

echo "✓ CHANGELOG.md properly updated for version $VERSION"
