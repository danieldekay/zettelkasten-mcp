#!/bin/bash
# Code quality check script

set -e

echo "🔍 Running comprehensive code quality checks..."

# Formatting and linting
echo "1. 📝 Formatting and linting with ruff..."
uv run ruff check . --fix
uv run ruff format .

# Type checking
echo "2. 🔍 Type checking with mypy..."
uv run mypy src/

# Security scanning
echo "3. 🔒 Security scanning with bandit..."
uv run bandit -r src/

# Dependency vulnerabilities
echo "4. 🛡️ Checking dependencies with safety..."
uv run safety check

# Tests with coverage
echo "5. 🧪 Running tests with coverage..."
uv run pytest --cov --cov-report=html --cov-report=term-missing

echo ""
echo "✅ All quality checks completed!"
echo "📊 Coverage report available in htmlcov/index.html"
