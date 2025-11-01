.ONESHELL:
SHELL=/bin/bash
ENV_NAME=coros_data_extractor
UV_VERSION=0.6.10
PYTHON_VERSION=3.12
.PHONY: install format lint

.SILENT: install

install:
# 	pyenv install -s 3.12
# 	pyenv local 3.12
	pip install --upgrade pip
	pip install uv==$(UV_VERSION)
# 	uv python install 3.12
	uv venv --python=python$(PYTHON_VERSION) --clear
	uv sync --all-groups
# 	uv run pre-commit install
# 	uv run ipython kernel install --user --name $(ENV_NAME)

.PHONY: linter
linter:
	$(info ########################)
	$(info ###      linter      ###)
	$(info ########################)
	@output="$$(uv run ruff check --fix 2>&1)"; \
	if [ -z "$$output" ]; then echo "ok"; else printf "%s\n" "$$output"; fi; \
	echo ""
 
.PHONY: format
format:
	$(info #########################)
	$(info ###      format       ###)
	$(info #########################)
	@output="$$(uv run ruff format 2>&1)"; \
	if [ -z "$$output" ]; then echo "ok"; else printf "%s\n" "$$output"; fi; \
	echo ""

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	rm -rf `find -type d -name .ipynb_checkpoints`
	rm -rf `find -type d -name *.egg-info`