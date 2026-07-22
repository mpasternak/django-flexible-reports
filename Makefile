.PHONY: clean-pyc clean-build docs help demo demo-grappelli demo-reset
.DEFAULT_GOAL := help

# The demo project. It lives in demo/ and runs on SQLite, so no services are
# needed. django-grappelli is not a dependency of this package, hence the
# --with for the grappelli flavour.
DEMO_MANAGE := uv run python demo/manage.py
DEMO_MANAGE_GRAPPELLI := DJANGO_SETTINGS_MODULE=demo.settings_grappelli \
	uv run --with django-grappelli python demo/manage.py

define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

clean: clean-build clean-pyc

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

lint: ## check style with flake8
	flake8 flexible_reports tests

test: ## run tests quickly with the default Python
	pytest tests

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	coverage run --source flexible_reports runtests.py tests
	coverage report -m
	coverage html
	open htmlcov/index.html

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/django-flexible-reports.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ flexible_reports
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

release: clean ## package and upload a release
	python setup.py sdist upload
	python setup.py bdist_wheel upload

sdist: clean ## package
	python setup.py sdist
	ls -l dist

demo: ## run the demo project with the plain Django admin on :8000
	$(DEMO_MANAGE) migrate --noinput
	$(DEMO_MANAGE) seed_demo
	$(DEMO_MANAGE) runserver 127.0.0.1:8000

demo-grappelli: ## run the demo project with django-grappelli on :8001
	$(DEMO_MANAGE_GRAPPELLI) migrate --noinput
	$(DEMO_MANAGE_GRAPPELLI) seed_demo
	$(DEMO_MANAGE_GRAPPELLI) runserver 127.0.0.1:8001

demo-reset: ## throw the demo database away (next `make demo` rebuilds it)
	rm -f demo/db.sqlite3
