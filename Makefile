.ONESHELL:
SHELL=/bin/bash
ENV_NAME=coros_data_extractor

.SILENT: install format lint check

install:
	@if ! command -v uv &> /dev/null; then \
		echo "uv not found. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "Please restart your shell or run: source ~/.cargo/env"; \
		echo "Then run 'make install' again."; \
		exit 1; \
	fi
	uv sync --all-extras
	uv run ipython kernel install --user --name $(ENV_NAME)
	uv run pre-commit install

format:
	$(info Running ruff format...)
	uv run ruff format .
	echo ""

lint:
	$(info Running ruff check...)
	uv run ruff check . --fix
	echo ""

check:
	$(info Running ruff check (no fix)...)
	uv run ruff check .
	echo ""
