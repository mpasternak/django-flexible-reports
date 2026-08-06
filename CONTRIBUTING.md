# Contributing

Contributions are welcome and appreciated. Every bit helps, and credit is
always given.

## Ways to contribute

### Report a bug

Open an issue at
<https://github.com/mpasternak/django-flexible-reports/issues> and include:

* your operating system, Python version and Django version;
* anything unusual about your setup (grappelli installed? which database?);
* the exact steps that reproduce the problem, and the traceback if there is
  one.

### Fix a bug or implement a feature

Issues tagged *bug* or *feature* are open to whoever wants to take them. If an
issue is not tagged and you would like to work on it, say so in a comment
first, so nobody duplicates the work.

### Improve the documentation

The manual in `docs/` is Markdown, built with
[MkDocs](https://www.mkdocs.org/) and the
[Material](https://squidfunk.github.io/mkdocs-material/) theme, and published
to <https://mpasternak.github.io/django-flexible-reports/>. Corrections to it
— or to docstrings, or a blog post elsewhere — are as welcome as code.

### Propose a feature

File an issue, explain how the feature would work, and keep the scope as
narrow as you can. This is a volunteer-driven project, so a small,
self-contained proposal has much better odds than a large one.

## Setting up for local development

The project is managed with [uv](https://docs.astral.sh/uv/).

1.  Fork the repository on GitHub and clone your fork:

    ```console
    $ git clone git@github.com:your_name_here/django-flexible-reports.git
    $ cd django-flexible-reports
    ```

2.  Create the environment and install everything, including the test and lint
    extras:

    ```console
    $ uv sync --all-extras
    ```

    `uv` creates `.venv/` and installs the package in editable mode; there is
    no `setup.py` to run.

3.  Install the pre-commit hooks. `pre-commit` is not a declared
    dependency, so run it as a tool:

    ```console
    $ uvx pre-commit install
    ```

4.  Create a branch:

    ```console
    $ git checkout -b name-of-your-bugfix-or-feature
    ```

## Running the tests

The test suite runs against **PostgreSQL** (see `tests/settings.py`). The
repository ships a `docker-compose.yml` that starts a matching server:

```console
$ docker compose up -d db
```

`tests/settings.py` connects to database `flexible_reports` as user
`postgres` with no password, on `$POSTGRES_HOST` (default `localhost`) and
`$POSTGRES_PORT` (default `5432`), so point those at your own server if you
already run one.

Then:

```console
$ uv run pytest
```

`pytest` picks up `--ds=tests.settings` from `pyproject.toml`, so no extra
flags are needed. Useful variations:

```console
$ uv run pytest --cov=flexible_reports          # with coverage, as CI runs it
$ uv run pytest test_app/tests/test_models      # one directory
$ uv run pytest test_app/tests/test_adapters.py::test_report    # one test
```

### The grappelli tests

`django-grappelli` is deliberately **not** a declared dependency: the suite has
to pass without it, and the grappelli-specific tests skip themselves when it is
absent. Because grappelli ships its own `admin/change_form.html`, which shadows
Django's, it gets a run of its own:

```console
$ uv run --with django-grappelli pytest test_app/tests/test_admin/test_grappelli.py
```

### The demo project

`demo/` is a small, self-contained project on SQLite that exercises the whole
feature set. It is the fastest way to see a change in a browser:

```console
$ make demo             # stock Django admin,     http://127.0.0.1:8000/
$ make demo-grappelli   # django-grappelli admin, http://127.0.0.1:8001/
$ make demo-reset       # throw the demo database away
```

Log into the admin as **`admin` / `admin`**. `make demo-grappelli` uses
`uv run --with django-grappelli` for the same reason as the tests above.

## Style and linting

Formatting and linting are done by [ruff](https://docs.astral.sh/ruff/). It is
pinned in the `lint` extra in `pyproject.toml` and kept in lock-step with the
`rev` of `astral-sh/ruff-pre-commit` in `.pre-commit-config.yaml` — if you bump
one, bump the other, or CI and the hook will disagree. Do not run
`uv run --with ruff`: that would silently fetch a different version.

```console
$ uv run ruff check .
$ uv run ruff format --check .
```

Running the hooks over the whole tree does the same and a little more
(trailing whitespace, end-of-file, YAML syntax, private keys):

```console
$ uvx pre-commit run --all-files
```

## Building the documentation

```console
$ make docs
```

That runs `mkdocs serve` and rebuilds on every save. To reproduce exactly what
CI does — including turning every warning into an error — build it:

```console
$ uv run --with mkdocs-material --with pymdown-extensions mkdocs build --strict
```

Documentation dependencies live in `docs/requirements.txt`, not in
`pyproject.toml`: nobody installing the package needs MkDocs.

## What CI checks

Every pull request runs
[`.github/workflows/tests.yml`](https://github.com/mpasternak/django-flexible-reports/blob/master/.github/workflows/tests.yml), which is:

|                | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 | Python 3.14 |
|----------------|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|
| Django 5.2 LTS |      ✔      |      ✔      |      ✔      |      ✔      |      ✔      |
| Django 6.0     |      —      |      —      |      ✔      |      ✔      |      ✔      |
| Django 6.1     |      —      |      —      |      ✔      |      ✔      |      ✔      |

Django 6.0 and 6.1 need Python 3.12+, so those legs are excluded. Each leg runs
the suite against a PostgreSQL service container, then the grappelli test
separately. A `lint` job runs `ruff check` and `ruff format --check`.

[`.github/workflows/docs.yml`](https://github.com/mpasternak/django-flexible-reports/blob/master/.github/workflows/docs.yml) builds the manual
with `--strict` on every pull request, and deploys to GitHub Pages only from
`master`.

## Pull request guidelines

1.  **Include tests.** A bug fix should come with a test that fails without it.
2.  **Update the documentation.** If the change is user-visible, the relevant
    page under `docs/` — and the feature list in `README.md` — should reflect
    it.
3.  **Add a `HISTORY.md` entry** under the topmost *(unreleased)* heading,
    written for someone upgrading rather than for someone reading the diff.
4.  **Keep the matrix green.** The change has to work on Python 3.10–3.14 with
    Django 5.2, and on Python 3.12–3.14 with Django 6.0 and 6.1. If you cannot
    run all of them locally, push the branch and let GitHub Actions tell you.
5.  **New user-facing strings go through `gettext`.** The package is
    translated (`flexible_reports/locale/`, currently Polish).

## Releasing

For maintainers:

```console
$ uv run bump-my-version bump patch   # or minor / major
$ make release
```

`bump-my-version` updates `flexible_reports/__init__.py` and
`pyproject.toml`, commits and tags; `make release` builds the sdist and wheel
with `uv build` and uploads them with `uv publish`.
