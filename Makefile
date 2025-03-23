.ONESHELL:
SHELL=/bin/bash
ENV_NAME=coros_data_extractor

.SILENT: install

install:
	pyenv install -s 3.12
	pyenv local 3.12
	pip install --upgrade pip
	pip install poetry
	poetry install --no-root
	poetry run ipython kernel install --user --name $(ENV_NAME)