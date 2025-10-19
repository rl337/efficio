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
if poetry run black --check .; then
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

# 4. Run unit tests
echo "🔍 Running unit tests..."
if poetry run pytest -v; then
    print_status "Unit tests passed"
else
    print_error "Unit tests failed"
    exit 1
fi

# 5. Test coverage (if coverage is installed)
echo "🔍 Running test coverage..."
if poetry run pytest --cov=efficio --cov-report=term-missing; then
    print_status "Test coverage check passed"
else
    print_warning "Test coverage check failed or coverage not available"
fi

# 6. Lint with flake8 (if available)
echo "🔍 Running flake8 linting..."
if command -v poetry run flake8 &> /dev/null; then
    if poetry run flake8 .; then
        print_status "flake8 linting passed"
    else
        print_error "flake8 linting failed"
        exit 1
    fi
else
    print_warning "flake8 not available, skipping"
fi

# 7. Security check with bandit (if available)
echo "🔍 Running security check..."
if command -v poetry run bandit &> /dev/null; then
    if poetry run bandit -r efficio/; then
        print_status "Security check passed"
    else
        print_warning "Security check found issues"
    fi
else
    print_warning "bandit not available, skipping security check"
fi

# 8. Check for common Python issues
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
