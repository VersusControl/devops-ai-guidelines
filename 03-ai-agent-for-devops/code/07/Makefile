.PHONY: help install run clean test

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make run      - Run the AI logging agent"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Clean up generated files"

install:
	pip install -r requirements.txt

run:
	python -m src

test:
	python -m pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
