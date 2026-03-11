# ══════════════════════════════════════════════════════════════════════════════
#  ZOYD - Autonomous Agent Loop for Claude Code
# ══════════════════════════════════════════════════════════════════════════════
SHELL := /bin/bash
.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────────────────────────────
# Colors - Funereal Purple/Violet Theme
# ─────────────────────────────────────────────────────────────────────────────
PURPLE := \033[95m
VIOLET := \033[35m
CYAN := \033[96m
YELLOW := \033[93m
RED := \033[91m
GRAY := \033[90m
BOLD := \033[1m
DIM := \033[2m
RESET := \033[0m

# ─────────────────────────────────────────────────────────────────────────────
# Project Config
# ─────────────────────────────────────────────────────────────────────────────
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
PROJECT_NAME := zoyd

# ─────────────────────────────────────────────────────────────────────────────
# ASCII Art Banner - Mind Flayer Theme
# ─────────────────────────────────────────────────────────────────────────────
define BANNER
$(PURPLE)
    ┌─────────────────────────────────────────────────────────────────────┐
    │$(VIOLET)              ___                                                   $(PURPLE)│
    │$(VIOLET)             /   \                                                  $(PURPLE)│
    │$(VIOLET)            / o o \        ╔═══════════════════════════════╗        $(PURPLE)│
    │$(VIOLET)           |   ∧   |       ║$(BOLD)$(PURPLE)           Z O Y D           $(RESET)$(VIOLET)║        $(PURPLE)│
    │$(VIOLET)           | \|||/ |       ║$(DIM)   autonomous agent loop      $(RESET)$(VIOLET)║        $(PURPLE)│
    │$(VIOLET)            \ ||| /        ║$(DIM)      for claude code         $(RESET)$(VIOLET)║        $(PURPLE)│
    │$(VIOLET)             \===//        ╚═══════════════════════════════╝        $(PURPLE)│
    │$(VIOLET)              |||                                                   $(PURPLE)│
    │$(GRAY)          "The mind flayer guides the loop..."                     $(PURPLE)│
    └─────────────────────────────────────────────────────────────────────┘
$(RESET)
endef
export BANNER

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo -e "$$BANNER"
	@echo -e "$(PURPLE)$(BOLD)  Available Commands$(RESET)"
	@echo -e "$(GRAY)  ─────────────────────────────────────────────────────────────$(RESET)"
	@echo ""
	@echo -e "  $(VIOLET)Installation$(RESET)"
	@echo -e "    $(CYAN)make install$(RESET)         Install in local venv for development"
	@echo -e "    $(CYAN)make install-global$(RESET)  Install via pipx for global CLI access"
	@echo -e "    $(CYAN)make uninstall$(RESET)       Remove from pipx"
	@echo ""
	@echo -e "  $(VIOLET)Development$(RESET)"
	@echo -e "    $(CYAN)make venv$(RESET)            Create virtual environment"
	@echo -e "    $(CYAN)make dev$(RESET)             Install in editable mode with dev deps"
	@echo ""
	@echo -e "  $(VIOLET)Testing$(RESET)"
	@echo -e "    $(CYAN)make test$(RESET)            Run full test suite"
	@echo -e "    $(CYAN)make test-one$(RESET)        Run specific test (TEST=name)"
	@echo ""
	@echo -e "  $(VIOLET)Quality$(RESET)"
	@echo -e "    $(CYAN)make lint$(RESET)            Run ruff linter"
	@echo -e "    $(CYAN)make fmt$(RESET)             Format with ruff or black"
	@echo -e "    $(CYAN)make check$(RESET)           Pre-commit style checks"
	@echo ""
	@echo -e "  $(VIOLET)CI$(RESET)"
	@echo -e "    $(CYAN)make ci-local$(RESET)        Simulate CI pipeline locally"
	@echo -e "    $(CYAN)make pre-release$(RESET)     Full global project check before releasing"
	@echo ""
	@echo -e "  $(VIOLET)Version & Release$(RESET)"
	@echo -e "    $(CYAN)make version$(RESET)         Show current version"
	@echo -e "    $(CYAN)make bump-patch$(RESET)      Bump patch version (0.0.X)"
	@echo -e "    $(CYAN)make bump-minor$(RESET)      Bump minor version (0.X.0)"
	@echo -e "    $(CYAN)make bump-major$(RESET)      Bump major version (X.0.0)"
	@echo -e "    $(CYAN)make publish-dry$(RESET)     Test PyPI publish (dry run)"
	@echo -e "    $(CYAN)make publish$(RESET)         Publish to PyPI"
	@echo ""
	@echo -e "  $(VIOLET)Utility$(RESET)"
	@echo -e "    $(CYAN)make clean$(RESET)           Remove build artifacts and caches"
	@echo ""

# ═══════════════════════════════════════════════════════════════════════════════
#  INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: venv
venv:
	@echo -e "$(PURPLE)$(BOLD)Creating virtual environment...$(RESET)"
	@python3 -m venv $(VENV)
	@echo -e "$(CYAN)✓ Virtual environment created at $(VENV)$(RESET)"

.PHONY: install
install: venv dev
	@echo -e "$(PURPLE)$(BOLD)✓ Installation complete$(RESET)"

.PHONY: dev
dev:
	@if [ ! -d "$(VENV)" ]; then \
		echo -e "$(YELLOW)Creating venv first...$(RESET)"; \
		python3 -m venv $(VENV); \
	fi
	@echo -e "$(PURPLE)$(BOLD)Installing in editable mode with dev dependencies...$(RESET)"
	@$(PIP) install -e ".[dev]" --quiet
	@echo -e "$(CYAN)✓ Installed zoyd in development mode$(RESET)"

.PHONY: install-global
install-global:
	@echo -e "$(PURPLE)$(BOLD)Installing zoyd globally via pipx...$(RESET)"
	@if ! command -v pipx &> /dev/null; then \
		echo -e "$(RED)Error: pipx not found. Install with: pip install pipx$(RESET)"; \
		exit 1; \
	fi
	@pipx install -e . --force
	@echo -e "$(CYAN)✓ Zoyd installed globally$(RESET)"
	@echo -e "$(GRAY)  Run 'zoyd --version' to verify$(RESET)"

.PHONY: uninstall
uninstall:
	@echo -e "$(PURPLE)$(BOLD)Uninstalling zoyd from pipx...$(RESET)"
	@pipx uninstall zoyd || true
	@echo -e "$(CYAN)✓ Zoyd uninstalled$(RESET)"

# ═══════════════════════════════════════════════════════════════════════════════
#  TESTING
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: test
test:
	@echo -e "$(PURPLE)$(BOLD)Running test suite...$(RESET)"
	@$(PYTEST) tests/ -v
	@echo -e "$(CYAN)✓ Tests complete$(RESET)"

.PHONY: test-one
test-one:
	@if [ -z "$(TEST)" ]; then \
		echo -e "$(RED)Error: Specify test with TEST=name$(RESET)"; \
		echo -e "$(GRAY)  Example: make test-one TEST=test_parse_tasks$(RESET)"; \
		exit 1; \
	fi
	@echo -e "$(PURPLE)$(BOLD)Running test: $(TEST)$(RESET)"
	@$(PYTEST) tests/ -v -k "$(TEST)"

# ═══════════════════════════════════════════════════════════════════════════════
#  CODE QUALITY
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: lint
lint:
	@echo -e "$(PURPLE)$(BOLD)Running linter...$(RESET)"
	@if command -v ruff &> /dev/null; then \
		ruff check zoyd/ tests/; \
	elif [ -f "$(VENV)/bin/ruff" ]; then \
		$(VENV)/bin/ruff check zoyd/ tests/; \
	else \
		echo -e "$(YELLOW)ruff not found, running basic Python syntax check...$(RESET)"; \
		$(PYTHON) -m py_compile zoyd/*.py; \
	fi
	@echo -e "$(CYAN)✓ Lint complete$(RESET)"

.PHONY: fmt
fmt:
	@echo -e "$(PURPLE)$(BOLD)Formatting code...$(RESET)"
	@if command -v ruff &> /dev/null; then \
		ruff format zoyd/ tests/; \
	elif [ -f "$(VENV)/bin/ruff" ]; then \
		$(VENV)/bin/ruff format zoyd/ tests/; \
	elif command -v black &> /dev/null; then \
		black zoyd/ tests/; \
	else \
		echo -e "$(YELLOW)No formatter found (ruff or black)$(RESET)"; \
	fi
	@echo -e "$(CYAN)✓ Formatting complete$(RESET)"

.PHONY: check
check: lint
	@echo -e "$(PURPLE)$(BOLD)Running pre-commit checks...$(RESET)"
	@$(PYTHON) -m py_compile zoyd/*.py tests/*.py
	@echo -e "$(CYAN)✓ All checks passed$(RESET)"

# ═══════════════════════════════════════════════════════════════════════════════
#  CI
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: ci-local
ci-local: clean venv dev lint test
	@echo -e "$(PURPLE)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo -e "$(CYAN)✓ CI pipeline simulation complete$(RESET)"
	@echo -e "$(PURPLE)$(BOLD)════════════════════════════════════════$(RESET)"

# Full pre-release check: installs globally via pipx, runs lint + unit tests,
# verifies the CLI works end-to-end, and prints the release version.
.PHONY: pre-release
pre-release: clean dev
	@echo -e "$(PURPLE)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo -e "$(VIOLET)$(BOLD)  PRE-RELEASE CHECK$(RESET)"
	@echo -e "$(PURPLE)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo ""
	@echo -e "$(PURPLE)$(BOLD)[1/5] Lint...$(RESET)"
	@$(MAKE) --no-print-directory lint
	@echo ""
	@echo -e "$(PURPLE)$(BOLD)[2/5] Unit tests (excluding integration)...$(RESET)"
	@$(PYTEST) tests/ -v --tb=short -x \
		--ignore=tests/test_redis_integration.py \
		--ignore=tests/test_vectors_integration.py \
		--ignore=tests/test_session_integration.py
	@echo ""
	@echo -e "$(PURPLE)$(BOLD)[3/5] Installing globally via pipx...$(RESET)"
	@if ! command -v pipx &> /dev/null; then \
		echo -e "$(RED)Error: pipx not found. Install with: pip install pipx$(RESET)"; \
		exit 1; \
	fi
	@pipx install -e . --force --quiet
	@echo -e "$(CYAN)  ✓ pipx install complete$(RESET)"
	@echo ""
	@echo -e "$(PURPLE)$(BOLD)[4/5] Smoke-testing global CLI...$(RESET)"
	@zoyd --version
	@zoyd --help > /dev/null
	@echo -e "$(CYAN)  ✓ CLI works$(RESET)"
	@echo ""
	@echo -e "$(PURPLE)$(BOLD)[5/5] Version check...$(RESET)"
	@VERSION=$$(grep -Po '(?<=version = ")[^"]+' pyproject.toml); \
	echo -e "$(CYAN)  Ready to release: $(BOLD)$$VERSION$(RESET)"
	@echo ""
	@echo -e "$(PURPLE)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo -e "$(CYAN)✓ Pre-release checks passed$(RESET)"
	@echo -e "$(PURPLE)$(BOLD)════════════════════════════════════════$(RESET)"

# ═══════════════════════════════════════════════════════════════════════════════
#  VERSION & RELEASE
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: version
version:
	@echo -e "$(PURPLE)$(BOLD)Current version:$(RESET)"
	@grep -Po '(?<=version = ")[^"]+' pyproject.toml

.PHONY: bump-patch
bump-patch:
	@echo -e "$(PURPLE)$(BOLD)Bumping patch version...$(RESET)"
	@CURRENT=$$(grep -Po '(?<=version = ")[^"]+' pyproject.toml); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(CYAN)✓ Version bumped: $$CURRENT → $$NEW_VERSION$(RESET)"

.PHONY: bump-minor
bump-minor:
	@echo -e "$(PURPLE)$(BOLD)Bumping minor version...$(RESET)"
	@CURRENT=$$(grep -Po '(?<=version = ")[^"]+' pyproject.toml); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(CYAN)✓ Version bumped: $$CURRENT → $$NEW_VERSION$(RESET)"

.PHONY: bump-major
bump-major:
	@echo -e "$(PURPLE)$(BOLD)Bumping major version...$(RESET)"
	@CURRENT=$$(grep -Po '(?<=version = ")[^"]+' pyproject.toml); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(CYAN)✓ Version bumped: $$CURRENT → $$NEW_VERSION$(RESET)"

.PHONY: publish-dry
publish-dry:
	@echo -e "$(PURPLE)$(BOLD)Testing PyPI publish (dry run)...$(RESET)"
	@$(PYTHON) -m build
	@$(PYTHON) -m twine check dist/*
	@echo -e "$(CYAN)✓ Package ready for publishing$(RESET)"

.PHONY: publish
publish:
	@echo -e "$(PURPLE)$(BOLD)Publishing to PyPI...$(RESET)"
	@echo -e "$(YELLOW)Warning: This will publish to the real PyPI!$(RESET)"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ]
	@$(PYTHON) -m build
	@$(PYTHON) -m twine upload dist/*
	@echo -e "$(CYAN)✓ Published to PyPI$(RESET)"

# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: clean
clean:
	@echo -e "$(PURPLE)$(BOLD)Cleaning build artifacts...$(RESET)"
	@rm -rf build/ dist/ *.egg-info .eggs/
	@rm -rf .pytest_cache/ .ruff_cache/ __pycache__/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo -e "$(CYAN)✓ Clean complete$(RESET)"

.PHONY: clean-all
clean-all: clean
	@echo -e "$(PURPLE)$(BOLD)Removing virtual environment...$(RESET)"
	@rm -rf $(VENV)
	@echo -e "$(CYAN)✓ Full clean complete$(RESET)"
