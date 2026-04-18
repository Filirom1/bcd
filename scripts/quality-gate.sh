#!/bin/bash
# Quality Gate Script for BCD Project
# Constitution Principle #11: Quality Gate Process
#
# This script performs automated post-implementation validation checks
# before code can be merged. All checks must pass for merge approval.

set -e  # Exit on first failure

echo "🚦 BCD Quality Gate - Post-Implementation Validation"
echo "=================================================="
echo ""

# Track overall status
FAILED_CHECKS=0

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to report check status
report_check() {
    local check_name="$1"
    local status="$2"
    local details="$3"

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $check_name"
        [ -n "$details" ] && echo "   $details"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ FAIL${NC}: $check_name"
        [ -n "$details" ] && echo "   $details"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  WARN${NC}: $check_name"
        [ -n "$details" ] && echo "   $details"
    fi
    echo ""
}

echo "📋 Check 1: Test Suite Execution"
echo "--------------------------------"
if pytest tests/ -v --tb=short; then
    report_check "All tests pass (unit, integration, e2e)" "PASS"
else
    report_check "All tests pass (unit, integration, e2e)" "FAIL" "One or more tests failed. Review output above."
fi

echo "📋 Check 2: TODO/FIXME/HACK Detection"
echo "-------------------------------------"
# Search for TODO/FIXME/HACK in production code (exclude tests, migrations, docs)
TODO_RESULTS=$(rg "TODO|FIXME|HACK" src/ --type py 2>/dev/null || true)
if [ -z "$TODO_RESULTS" ]; then
    report_check "Zero TODO/FIXME/HACK comments in production code" "PASS"
else
    report_check "Zero TODO/FIXME/HACK comments in production code" "FAIL" "Found in:\n$TODO_RESULTS"
fi

echo "📋 Check 3: Fake/Mock Implementation Detection"
echo "----------------------------------------------"
# Search for common fake/mock patterns in production code
FAKE_RESULTS=$(rg "fake|mock|stub|placeholder|not implemented" src/ --type py -i --ignore-case 2>/dev/null || true)
# Filter out legitimate test/mock usage (like unittest.mock imports)
FAKE_RESULTS=$(echo "$FAKE_RESULTS" | grep -v "unittest.mock" | grep -v "from unittest import mock" | grep -v "import mock" || true)
if [ -z "$FAKE_RESULTS" ]; then
    report_check "Zero fake/mock/placeholder implementations" "PASS"
else
    report_check "Zero fake/mock/placeholder implementations" "FAIL" "Found in:\n$FAKE_RESULTS"
fi

echo "📋 Check 4: Test Coverage"
echo "-------------------------"
# Run coverage check with 80% threshold
COVERAGE_OUTPUT=$(pytest --cov=src --cov-report=term-missing --cov-fail-under=80 --tb=no -q 2>&1 || true)
if echo "$COVERAGE_OUTPUT" | grep -q "Required test coverage of 80% reached"; then
    COVERAGE_PERCENT=$(echo "$COVERAGE_OUTPUT" | grep -oP '\d+%' | tail -1)
    report_check "Test coverage ≥80% for new code" "PASS" "Coverage: $COVERAGE_PERCENT"
else
    COVERAGE_PERCENT=$(echo "$COVERAGE_OUTPUT" | grep -oP '\d+%' | tail -1 || echo "Unknown")
    report_check "Test coverage ≥80% for new code" "FAIL" "Coverage: $COVERAGE_PERCENT (required: ≥80%)"
fi

echo "📋 Check 5: Library-First Approach (Principle #2)"
echo "-------------------------------------------------"
# Check for common anti-patterns indicating custom implementations
CUSTOM_IMPL=$(rg "from scratch|custom implementation|reinvent|roll our own" src/ --type py -i 2>/dev/null || true)
# Also check for manual date/time parsing, HTTP clients, etc. that should use libraries
CUSTOM_IMPL+=$(rg "def parse_date|def parse_datetime|def http_request|def http_get|def http_post" src/ --type py 2>/dev/null | grep -v "test_" || true)
if [ -z "$CUSTOM_IMPL" ]; then
    report_check "No custom implementations where libraries exist" "PASS"
else
    report_check "No custom implementations where libraries exist" "WARN" "Review these implementations:\n$CUSTOM_IMPL"
fi

echo "=================================================="
echo "📊 Quality Gate Summary"
echo "=================================================="
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✅ All automated checks PASSED${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run '/speckit.analyze' to verify constitution re-validation"
    echo "2. Request Claude AI architect review"
    echo "3. Ensure no CRITICAL/MAJOR/MEDIUM findings before merge"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $FAILED_CHECKS check(s) FAILED${NC}"
    echo ""
    echo "Quality gate BLOCKED. Fix the issues above before merge."
    echo ""
    exit 1
fi
