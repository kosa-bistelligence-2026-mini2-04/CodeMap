#!/bin/bash
# Test a single language in clean Docker environment

set -e

LANGUAGE=${1:-"go"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Map language name to fixture directory
case $LANGUAGE in
    go) FIXTURE="sample_go" ;;
    java) FIXTURE="sample_java" ;;
    scala) FIXTURE="sample_scala" ;;
    ruby) FIXTURE="sample_ruby" ;;
    dart) FIXTURE="sample_dart" ;;
    c) FIXTURE="sample_c" ;;
    cpp) FIXTURE="sample_cpp" ;;
    csharp) FIXTURE="sample_csharp" ;;
    vb) FIXTURE="sample_vb" ;;
    *) echo "Unknown language: $LANGUAGE"; exit 1 ;;
esac

FIXTURE_PATH="$REPO_ROOT/tests/fixtures/$FIXTURE"

echo "=========================================="
echo "Testing: $LANGUAGE ($FIXTURE)"
echo "=========================================="
echo ""

# Build base image
echo "Building base Docker image..."
docker build -t cicada-base -f "$SCRIPT_DIR/Dockerfile.base" "$REPO_ROOT"
echo ""

# Run test
echo "Running test in clean container..."
echo ""

docker run --rm -it \
    -v "$FIXTURE_PATH:/workspace/project:ro" \
    cicada-base \
    bash -c "
        cd /workspace/project && \
        echo '=== Running: python -m cicada claude ===' && \
        python -m cicada claude 2>&1
    "
