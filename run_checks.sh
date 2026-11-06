#!/bin/bash

# Efficio Validation Script
# This script runs all automated tests, static checks, style linting, and validation
# as required by AGENTS.md

set -e  # Exit on any error

echo "🔍 Running Efficio validation checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Resolve paths independently of the caller's working directory. Prefer the
# project venv when present; Docker uses its existing Poetry installation.
cd "$(dirname "${BASH_SOURCE[0]}")"
case "${EFFICIO_CHECK_ENV:-auto}" in
    auto)
        if [ -x .venv/bin/python ]; then
            runner=("$PWD/.venv/bin/python" -m)
        else
            runner=(poetry run)
        fi
        ;;
    venv)
        if [ ! -x .venv/bin/python ]; then
            print_error "Missing .venv. Run ./scripts/setup_venv.sh first."
            exit 1
        fi
        runner=("$PWD/.venv/bin/python" -m)
        ;;
    docker) runner=(poetry run) ;;
    *) print_error "EFFICIO_CHECK_ENV must be auto, venv, or docker"; exit 1 ;;
esac

# Python itself takes -c, while tools run as modules in the venv.
run_python() {
    if [ "${runner[1]}" = "-m" ]; then
        "${runner[0]}" "$@"
    else
        "${runner[@]}" python "$@"
    fi
}

# 1. Type checking with MyPy
echo "🔍 Running MyPy type checking..."
if "${runner[@]}" mypy .; then
    print_status "MyPy type checking passed"
else
    print_error "MyPy type checking failed"
    exit 1
fi

# 2. Code formatting with Black
echo "🔍 Running Black code formatting check..."
if "${runner[@]}" black --check .; then
    print_status "Black formatting check passed"
else
    print_error "Black formatting check failed. Run Black in the selected development environment to fix formatting issues"
    exit 1
fi

# 3. Import sorting with isort
echo "🔍 Running isort import sorting check..."
if "${runner[@]}" isort --check-only .; then
    print_status "isort import sorting check passed"
else
    print_error "isort import sorting check failed. Run isort in the selected development environment to fix import issues"
    exit 1
fi

# 4. Run unit tests (once), with coverage when pytest-cov is installed.
#    A JUnit report goes to test-results/ so CI can summarise and upload it.
echo "🔍 Running unit tests..."
mkdir -p test-results
pytest_args=(-v --junitxml=test-results/junit.xml)
if run_python -c "import pytest_cov" 2>/dev/null; then
    pytest_args+=(--cov=efficio --cov-report=term-missing)
    coverage_enabled=1
else
    coverage_enabled=0
fi
if "${runner[@]}" pytest "${pytest_args[@]}"; then
    print_status "Unit tests passed"
else
    print_error "Unit tests failed"
    exit 1
fi
if [ "$coverage_enabled" = 0 ]; then
    print_warning "pytest-cov not installed; coverage not measured"
fi

# 5. Optional tools: run them only if installed, and say so plainly if not.
run_optional() {
    local tool="$1"; shift
    if ! run_python -c "import $tool" 2>/dev/null; then
        print_warning "$tool not installed, skipping"
        return
    fi
    echo "🔍 Running $tool..."
    if "${runner[@]}" "$@"; then
        print_status "$tool passed"
    else
        print_warning "$tool reported issues"
    fi
}
run_optional flake8 flake8 .
run_optional bandit bandit -q -r efficio/

# 6. Check for common Python issues
echo "🔍 Running additional Python checks..."

# Check for TODO/FIXME comments
if grep -r "TODO\|FIXME" efficio/ --exclude-dir=__pycache__; then
    print_warning "Found TODO/FIXME comments in code"
fi

# Check for print statements (should use logging)
if grep -r "print(" efficio/ --exclude-dir=__pycache__; then
    print_warning "Found print statements in code (consider using logging)"
fi

print_status "All validation checks completed successfully! 🎉"
