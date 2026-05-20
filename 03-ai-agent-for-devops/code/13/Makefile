.PHONY: help install run clean

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make run      - Run the Streamlit app"
	@echo "  make clean    - Clean up generated files"

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .streamlit/
