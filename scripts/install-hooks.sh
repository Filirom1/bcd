#!/bin/bash
#
# Install Git Hooks
#
# This script installs pre-commit hooks that prevent commits when tests fail.
# Run this script after cloning the repository.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "📦 Installing Git hooks..."

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
#
# Pre-commit hook: Run tests before allowing commit
# This prevents commits when tests fail

echo "🧪 Running tests before commit..."
echo ""

# Run all tests in order: unit (fastest) → integration → API → CLI (slowest)
# This follows the test pyramid pattern for faster feedback
# Use --tb=short for concise error output
# E2E tests are excluded for speed (run manually: pytest tests/e2e/ tests/cli/test_e2e*.py -v)
if pytest tests/unit tests/integration tests/api tests/cli --ignore-glob='*e2e*' --tb=short -q; then
    echo ""
    echo "✅ All tests passed! Proceeding with commit..."
    exit 0
else
    echo ""
    echo "❌ Tests failed! Commit blocked."
    echo ""
    echo "Fix the failing tests before committing, or use:"
    echo "  git commit --no-verify"
    echo "to skip this check (not recommended)."
    exit 1
fi
EOF

chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will:"
echo "  • Run unit, integration, API, and CLI tests (in that order) before each commit"
echo "  • Block the commit if any tests fail"
echo "  • Allow commit only when all tests pass"
echo ""
echo "Test execution order (test pyramid):"
echo "  1. Unit tests (fastest)"
echo "  2. Integration tests"
echo "  3. API tests"
echo "  4. CLI tests (excluding e2e tests)"
echo ""
echo "Note: E2E tests are excluded for speed."
echo "Run manually: pytest tests/e2e/ tests/cli/test_e2e*.py -v"
echo ""
echo "To bypass the hook (not recommended):"
echo "  git commit --no-verify"
