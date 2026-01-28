# VS Code Development Environment Setup - 2026 Best Practices

This document outlines the modern VS Code workspace configuration implemented for the Zettelkasten MCP Server project, following 2026 development best practices.

## 🚀 Key Improvements

### 1. Modern Python Tooling

**Ruff Integration** (Replaces Black + isort + flake8)

- Ultra-fast linting and formatting
- Comprehensive rule set covering security, performance, and style
- Configured in `pyproject.toml` with extensive rule selection

**Enhanced Development Dependencies**

- pytest 8.x with parallel testing (`pytest-xdist`)
- Comprehensive security tools (`bandit`, `safety`)
- Modern type checking with `mypy` 1.8+

### 2. VS Code Configuration

**Workspace Settings** ([zettelkasten-mcp.code-workspace](zettelkasten-mcp.code-workspace))

- Python environment auto-detection (`.venv`)
- Strict type checking with Pylance
- Format-on-save with comprehensive code actions
- GitHub Copilot integration with custom instructions

**Tasks** ([.vscode/tasks.json](.vscode/tasks.json))

- Full quality check pipeline
- Individual tool execution (lint, format, test, security)
- Pre-commit setup automation
- MCP server debugging support

**Launch Configurations** ([.vscode/launch.json](.vscode/launch.json))

- Debug MCP server with environment variables
- Test debugging with pytest integration
- Remote attach debugging capability
- Uses modern `debugpy` debugger

**Extensions** ([.vscode/extensions.json](.vscode/extensions.json))

- Curated list of essential Python development extensions
- Modern tools (Ruff, Pylance, GitHub Copilot)
- Excludes deprecated tools (Black, isort, flake8)

### 3. Code Quality Automation

**Pre-commit Hooks** ([.pre-commit-config.yaml](.pre-commit-config.yaml))

- Ruff linting and formatting
- MyPy type checking
- Security scanning with Bandit
- Dependency vulnerability checking
- Automated test execution on push

**Continuous Integration** ([.github/workflows/ci.yml](.github/workflows/ci.yml))

- Multi-Python version testing (3.10, 3.11, 3.12)
- UV package manager for faster installs
- Comprehensive quality checks (lint, type, security, test)
- Security scanning with Trivy
- Codecov integration for coverage reporting

### 4. Development Scripts

**Setup Script** ([scripts/setup-dev.sh](scripts/setup-dev.sh))

```bash
./scripts/setup-dev.sh
```

- Automated development environment setup
- Dependency installation with UV
- Pre-commit hooks configuration
- Initial quality checks

**Quality Check** ([scripts/quality-check.sh](scripts/quality-check.sh))

```bash
./scripts/quality-check.sh
```

- Comprehensive code quality pipeline
- Automated formatting and linting
- Security and dependency vulnerability scanning
- Test execution with coverage reporting

### 5. Enhanced Testing Configuration

**Pytest Configuration** (pyproject.toml)

- Strict configuration with comprehensive coverage
- HTML and terminal coverage reporting
- Test markers for organization (unit, integration, slow, security)
- Warning filters for clean test output

**Coverage Configuration**

- Branch coverage enabled
- Comprehensive exclusion patterns
- HTML reporting in `htmlcov/`
- Fail-under threshold at 85%

## 📁 File Structure

```
.vscode/
├── extensions.json          # Recommended extensions
├── launch.json             # Debug configurations (debugpy)
├── python.code-snippets    # Custom code snippets
├── settings.json           # Project-specific settings
└── tasks.json              # Development tasks

.github/
└── workflows/
    └── ci.yml              # CI/CD pipeline

scripts/
├── setup-dev.sh            # Development setup
└── quality-check.sh        # Quality assurance

Configuration Files:
├── .pre-commit-config.yaml # Pre-commit hooks
├── pyproject.toml          # Enhanced tool configuration
└── zettelkasten-mcp.code-workspace # VS Code workspace
```

## 🛠️ Quick Start

1. **Open the workspace:**

   ```bash
   code zettelkasten-mcp.code-workspace
   ```

2. **Install recommended extensions** when prompted

3. **Run setup script:**

   ```bash
   ./scripts/setup-dev.sh
   ```

4. **Start developing!**

## ⌨️ Key Shortcuts & Commands

### VS Code Tasks (Ctrl+Shift+P → Tasks: Run Task)

- `Install Dependencies` - UV sync with dev dependencies
- `Run Tests` - Execute test suite
- `Full Quality Check` - Complete CI pipeline locally
- `Lint with Ruff` - Code linting and auto-fix
- `Format with Ruff` - Code formatting
- `Type Check with MyPy` - Static type analysis
- `Security Check with Bandit` - Security vulnerability scan

### Debug Configurations (F5)

- `Debug MCP Server` - Debug server with environment setup
- `Debug Tests` - Debug test execution
- `Debug Current File` - Debug currently open Python file

### Code Snippets (Type prefix + Tab)

- `mcp-tool` - MCP server tool template
- `test-func` - Test function with AAA pattern
- `repo-method` - Repository method template
- `error-handler` - Error handling block
- `pydantic-model` - Pydantic model template

## 🔧 Tool Configuration

### Ruff (Modern Linting & Formatting)

- **Line length:** 88 characters
- **Target Python:** 3.10+
- **Rules:** Comprehensive security, performance, style rules
- **Auto-fix:** Enabled with format-on-save

### MyPy (Type Checking)

- **Mode:** Strict
- **Target:** src/ directory only
- **Ignores:** Missing imports (for external dependencies)

### Bandit (Security Scanning)

- **Target:** src/ directory
- **Config:** pyproject.toml
- **Excludes:** Tests (assert statements allowed)

### Pytest (Testing)

- **Coverage:** 85% threshold with branch coverage
- **Formats:** HTML + terminal reporting
- **Parallel:** Enabled with pytest-xdist
- **Markers:** Unit, integration, slow, security tests

## 🚨 Common Issues & Solutions

### Extension Formatter Conflicts

- Ruff extension not installed → Install from recommendations
- Multiple formatters → Settings prioritize Ruff
- Format-on-save not working → Check `.vscode/settings.json`

### Pre-commit Issues

- Hooks not running → `uv run pre-commit install`
- Ruff not found → `uv sync --dev` to install dependencies
- Tests failing in hooks → Fix tests before committing

### Debug Configuration

- Python interpreter not found → Select `.venv/bin/python` in VS Code
- Environment variables not loaded → Check `launch.json` env section
- Breakpoints not hitting → Ensure `justMyCode: false`

## 📈 Performance Benefits

- **Ruff**: 10-100x faster than Black+isort+flake8
- **UV**: 10-25x faster package installation
- **Parallel Testing**: Significantly faster test execution
- **Pre-commit**: Catch issues before CI/CD

## 🔄 Migration from Old Setup

If migrating from older configurations:

1. **Remove deprecated tools:**

   ```bash
   uv remove black isort flake8
   ```

2. **Install new tools:**

   ```bash
   uv add --dev ruff bandit safety
   ```

3. **Update VS Code settings:**
   - Remove Black/isort formatter settings
   - Add Ruff configuration

4. **Update CI/CD:**
   - Replace Black+isort with Ruff
   - Add security scanning steps

## 📚 Additional Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [Pre-commit Framework](https://pre-commit.com/)
- [GitHub Copilot Guide](https://docs.github.com/en/copilot)
- [VS Code Python Development](https://code.visualstudio.com/docs/python/python-tutorial)

---

*This setup follows 2026 Python development best practices with a focus on performance, security, and developer experience.*

