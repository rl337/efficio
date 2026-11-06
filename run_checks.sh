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

# Check if we're in a Docker container
if [ ! -f /.dockerenv ]; then
    print_warning "Not running in Docker container. AGENTS.md requires Docker for development."
    print_warning "Consider running: docker build -t efficio . && docker run -it -v \$(pwd):/app efficio"
fi

# 1. Type checking with MyPy
echo "🔍 Running MyPy type checking..."
if poetry run mypy .; then
    print_status "MyPy type checking passed"
else
    print_error "MyPy type checking failed"
    exit 1
fi

# 2. Code formatting with Black
echo "🔍 Running Black code formatting check..."
if poetry run black --check --diff .; then
    print_status "Black formatting check passed"
else
    print_error "Black formatting check failed. Run 'poetry run black .' to fix formatting issues"
    exit 1
fi

# 3. Import sorting with isort
echo "🔍 Running isort import sorting check..."
if poetry run isort --check-only .; then
    print_status "isort import sorting check passed"
else
    print_error "isort import sorting check failed. Run 'poetry run isort .' to fix import issues"
    exit 1
fi

# 4. Run unit tests (once), with coverage when pytest-cov is installed.
#    A JUnit report goes to test-results/ so CI can summarise and upload it.
echo "🔍 Running unit tests..."
mkdir -p test-results
pytest_args=(-v --junitxml=test-results/junit.xml)
if poetry run python -c "import pytest_cov" 2>/dev/null; then
    pytest_args+=(--cov=efficio --cov-report=term-missing)
    coverage_enabled=1
else
    coverage_enabled=0
fi
if poetry run pytest "${pytest_args[@]}"; then
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
    if ! poetry run python -c "import $tool" 2>/dev/null; then
        print_warning "$tool not installed, skipping"
        return
    fi
    echo "🔍 Running $tool..."
    if poetry run "$@"; then
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
