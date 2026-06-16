#!/bin/bash
# Release script for Catholic Knowledge Base
# Usage: ./scripts/release.sh [version]

set -e

VERSION=${1:-"1.0.0"}

echo "Building Catholic Knowledge Base v${VERSION}..."

# Tag the release
git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin "v${VERSION}"

echo ""
echo "Release v${VERSION} tagged and pushed!"
echo ""
echo "GitHub Actions will now build for:"
echo "  - macOS (Apple Silicon + Intel)"
echo "  - Windows (x64)"
echo "  - Linux (x64)"
echo ""
echo "Check progress at: https://github.com/<your-org>/<your-repo>/actions"
echo ""
echo "Once complete, create a release at:"
echo "  https://github.com/<your-org>/<your-repo>/releases/new?tag=v${VERSION}"
