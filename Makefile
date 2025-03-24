.ONESHELL:
SHELL=/bin/bash
ENV_NAME=coros_data_extractor

.SILENT: install isort black flake8 format lint

install:
	pyenv install -s 3.12
	pyenv local 3.12
	pip install --upgrade pip
	pip install poetry
	poetry install --no-root with dev
	poetry run ipython kernel install --user --name $(ENV_NAME)
	poetry run pre-commit install

isort:
	$(info Running isort...)
	$(eval output=$(shell poetry run isort .))
	@if [ -z "$(output)" ]; then echo "iSort complete."; else echo $(output); fi
	echo ""

black:
	$(info Running black...)
	$(eval output=$(shell poetry run black .))
	@if [ -z "$(output)" ]; then echo "Black formatting complete."; else echo $(output); fi
	echo ""

flake8:
	$(info Running flake8...)
	$(eval output=$(shell poetry run flake8 .))
	@if [ -z "$(output)" ]; then echo "flake8 linting complete."; else echo $(output); fi
	echo ""

format: isort black

lint: flake8
