#!/bin/bash
# Development setup script for Zettelkasten MCP Server

set -e

echo "🚀 Setting up Zettelkasten MCP Server development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies with uv..."
uv sync --all-extras --dev

# Set up pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
uv run pre-commit install

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/db data/notes

# Run initial checks
echo "🔍 Running initial code quality checks..."
echo "  - Linting with ruff..."
uv run ruff check . || echo "⚠️  Linting issues found (will be fixed)"

echo "  - Type checking with mypy..."
uv run mypy src/ || echo "⚠️  Type checking issues found"

echo "  - Security check with bandit..."
uv run bandit -r src/ || echo "⚠️  Security issues found"

echo "  - Running tests..."
uv run pytest --tb=short || echo "⚠️  Some tests failing"

echo "✅ Development environment setup complete!"
echo ""
echo "📝 Next steps:"
echo "   - Open VS Code: code ."
echo "   - Install recommended extensions when prompted"
echo "   - Start coding! 🎉"
echo ""
echo "📚 Useful commands:"
echo "   - Run tests: uv run pytest"
echo "   - Lint code: uv run ruff check ."
echo "   - Format code: uv run ruff format ."
echo "   - Type check: uv run mypy src/"
echo "   - Security check: uv run bandit -r src/"
echo "   - Run server: uv run python -m zettelkasten_mcp"
