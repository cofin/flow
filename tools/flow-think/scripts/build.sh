#!/usr/bin/env bash
# Build script for flow-think-mcp
# Uses Bun's bundler for single-file output with Node.js fallback

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "==> Building flow-think-mcp..."
echo ""

# Clean previous build
echo "    Cleaning dist/"
rm -rf dist/

# Detect runtime
if command -v bun &> /dev/null; then
    echo -e "    ${CYAN}Using Bun bundler (single-file build)${NC}"

    # Create dist directory
    mkdir -p dist

    # Build standalone executable with embedded Bun runtime
    echo "    Building standalone executable..."
    bun build src/index.ts \
        --compile \
        --minify \
        --outfile dist/flow-think-mcp

    # Also create JS bundle for Node.js fallback
    echo "    Building JS bundle for Node.js fallback..."
    bun build src/index.ts \
        --outfile dist/index.js \
        --target node \
        --format esm \
        --minify

    # Also generate type declarations using tsc
    echo "    Generating type declarations..."
    bun run tsc --emitDeclarationOnly --declaration --outDir dist 2>/dev/null || true

    # Add shebang for direct execution (if not already present)
    if ! head -1 dist/index.js | grep -q '^#!'; then
        echo "    Adding shebang..."
        TEMP_FILE=$(mktemp)
        echo '#!/usr/bin/env node' > "$TEMP_FILE"
        cat dist/index.js >> "$TEMP_FILE"
        mv "$TEMP_FILE" dist/index.js
    fi

    BUILD_MODE="bundled"
else
    echo -e "    ${YELLOW}Bun not available, falling back to tsc${NC}"

    # Ensure dependencies are installed
    if [[ ! -d "node_modules" ]]; then
        echo "    Installing dependencies..."
        if command -v npm &>/dev/null; then
            npm install --ignore-scripts 2>/dev/null || {
                echo -e "    ${RED}Failed to install dependencies${NC}"
                exit 1
            }
        else
            echo -e "    ${RED}npm not found — install Node.js or Bun${NC}"
            exit 1
        fi
    fi

    # Create dist directory
    mkdir -p dist

    # Run TypeScript compiler (try tsc directly, then npx)
    echo "    Compiling TypeScript..."
    if command -v tsc &>/dev/null; then
        tsc || { echo -e "    ${RED}tsc compilation failed${NC}"; exit 1; }
    elif command -v npx &>/dev/null; then
        npx tsc || { echo -e "    ${RED}npx tsc compilation failed${NC}"; exit 1; }
    else
        echo -e "    ${RED}tsc not found — install typescript or use Bun${NC}"
        exit 1
    fi

    # Add shebang for direct execution (if not already present)
    if [[ -f dist/index.js ]] && ! head -1 dist/index.js | grep -q '^#!'; then
        echo "    Adding shebang..."
        TEMP_FILE=$(mktemp)
        echo '#!/usr/bin/env node' > "$TEMP_FILE"
        cat dist/index.js >> "$TEMP_FILE"
        mv "$TEMP_FILE" dist/index.js
    fi

    BUILD_MODE="compiled"
fi

# Make entry point executable
echo "    Making dist/index.js executable..."
chmod +x dist/index.js

# Verify build
if [[ -f "dist/index.js" ]]; then
    echo ""
    echo -e "${GREEN}==> Build successful!${NC}"
    echo "    Output: dist/index.js"

    # Show size
    SIZE=$(ls -lh dist/index.js | awk '{print $5}')
    echo "    Size: $SIZE"

    # Count files
    FILE_COUNT=$(find dist -name "*.js" | wc -l)

    if [[ "$BUILD_MODE" == "bundled" ]]; then
        echo -e "    Mode: ${CYAN}Single-file bundle${NC}"
    else
        echo "    Files: $FILE_COUNT JavaScript files"
    fi
else
    echo -e "${RED}==> Build failed: dist/index.js not found${NC}"
    exit 1
fi

echo ""
echo "Run with:"
echo "  bun dist/index.js"
echo "  node dist/index.js"
