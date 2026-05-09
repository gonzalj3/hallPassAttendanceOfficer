PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: install test test-unit test-integration lint fmt type db-up db-down hooks clean

$(VENV)/bin/pip:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip

install: $(VENV)/bin/pip
	$(BIN)/pip install -e ".[dev]"
	$(BIN)/pre-commit install

test:
	$(BIN)/pytest

test-unit:
	$(BIN)/pytest tests/unit -q

test-integration:
	$(BIN)/pytest tests/integration -q

lint:
	$(BIN)/ruff check
	$(BIN)/ruff format --check

fmt:
	$(BIN)/ruff check --fix
	$(BIN)/ruff format

type:
	$(BIN)/mypy

db-up:
	docker compose up -d db

db-down:
	docker compose down

hooks:
	$(BIN)/pre-commit run --all-files

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov *.egg-info
