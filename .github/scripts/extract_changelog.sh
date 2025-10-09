#!/usr/bin/env bash
# Extracts the changelog section for a specific version from CHANGELOG.md

set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

CHANGELOG="CHANGELOG.md"

if [ ! -f "$CHANGELOG" ]; then
  echo "Error: CHANGELOG.md not found!"
  exit 1
fi

# Extract the section for this version
# - Start from ## [$VERSION] line
# - End at the next ## [ line (next version) or end of file
# - Remove the version header itself
SECTION=$(awk "/## \[$VERSION\]/{flag=1; next} /## \[/{flag=0} flag" "$CHANGELOG")

if [ -z "$SECTION" ]; then
  echo "Error: No changelog section found for version $VERSION"
  exit 1
fi

# Output the section with installation instructions appended
cat <<EOF
$SECTION

---

## Installation

\`\`\`bash
pip install tripwire-py==$VERSION
\`\`\`

## Quick Start

\`\`\`python
from tripwire import env

# Required variables (fail at import if missing)
API_KEY: str = env.require("API_KEY")
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")

# Optional variables with defaults
DEBUG: bool = env.optional("DEBUG", default=False)
PORT: int = env.optional("PORT", default=8000, min_val=1, max_val=65535)
\`\`\`

For full documentation, see the [GitHub repository](https://github.com/Daily-Nerd/TripWire).
EOF
