.PHONY: clean-pyc clean-build docs docs-build help demo demo-grappelli demo-reset
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

lint: ## check style and formatting with ruff
	uv run ruff check .
	uv run ruff format --check .

# The suite lives in test_app/tests; `tests/` holds only settings.py and
# urls.py. This target used to point at `tests`, so it collected nothing and
# still exited 0 -- a green `make test` that ran no tests at all.
test: ## run the test suite
	uv run pytest test_app/tests

test-grappelli: ## run the grappelli integration tests (optional dependency)
	uv run --with django-grappelli pytest test_app/tests/test_admin/test_grappelli.py

coverage: ## check code coverage and open the report
	uv run pytest test_app/tests --cov=flexible_reports --cov-report=term-missing --cov-report=html
	$(BROWSER) htmlcov/index.html

# The manual is prose written by hand in docs/*.md; there is no API
# autogeneration step. MkDocs and the Material theme are pinned in
# docs/requirements.txt and are deliberately not dependencies of the package,
# hence the --with flags.
MKDOCS := uv run --with mkdocs-material --with pymdown-extensions mkdocs

docs: ## serve the documentation locally, rebuilding on save
	$(MKDOCS) serve

docs-build: ## build the documentation exactly the way CI does
	$(MKDOCS) build --strict

release: clean ## package and upload a release
	uv build
	uv publish

sdist: clean ## package
	uv build --sdist
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
