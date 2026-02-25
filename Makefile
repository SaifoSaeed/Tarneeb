.PHONY: all run freeze deps

# Define the path to the virtual env's python executable
VENV_PYTHON = /home/saifo/Documents/Projects/Tarneeb/Tarneeb/bin/python

all: run

run:
	$(VENV_PYTHON) tarneeb.py

freeze:
	uv pip freeze > requirements.txt

deps:
	uv pip install -r requirements.txt

install:
	