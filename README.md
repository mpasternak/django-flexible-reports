# Django Flexible Reports

[![PyPI Version](https://img.shields.io/pypi/v/django-flexible-reports.svg)](https://pypi.org/project/django-flexible-reports/)
[![Python Version](https://img.shields.io/pypi/pyversions/django-flexible-reports.svg)](https://pypi.org/project/django-flexible-reports/)
[![Tests](https://github.com/mpasternak/django-flexible-reports/actions/workflows/tests.yml/badge.svg)](https://github.com/mpasternak/django-flexible-reports/actions/workflows/tests.yml)
[![Docs](https://github.com/mpasternak/django-flexible-reports/actions/workflows/docs.yml/badge.svg)](https://github.com/mpasternak/django-flexible-reports/actions/workflows/docs.yml)
[![License](https://img.shields.io/pypi/l/django-flexible-reports.svg)](LICENSE)

A framework for **database-defined reports** in Django.

Instead of hardcoding a report in a template or a view, you describe it in the
database — which rows it shows, which columns it has, how the cells are
formatted, how it is sorted — and edit all of that through the Django admin.
Your application code only picks a report, hands it a queryset and renders it
with one template tag:

```django
{% load flexible_reports_tags %}
{% flexible report %}
```

Rendering is done by [django-tables2](https://github.com/jieter/django-tables2),
so you get sortable headers, footers/totals and export for free.

## Supported Versions

|                | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 | Python 3.14 |
|----------------|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|
| Django 5.2 LTS |      ✔      |      ✔      |      ✔      |      ✔      |      ✔      |
| Django 6.0     |      —      |      —      |      ✔      |      ✔      |      ✔      |

Django 6.0 requires Python 3.12+. Django 4.2, 5.0 and 5.1 are no longer
supported or tested — the floor is Django 5.2 LTS.

## Documentation

The full documentation is at
<https://mpasternak.github.io/django-flexible-reports/>.

## Features

* **Reports live in the database, not in your code.** `Datasource`, `Table`,
  `Column`, `ColumnOrder`, `Report` and `ReportElement` are ordinary Django
  models with a full admin, so non-programmers can change what a report shows
  without a deployment.
* **Two query languages for selecting rows.** A `Datasource` narrows a base
  queryset using either [django-dsl](https://pypi.org/project/django-dsl/)
  (the default) or [DjangoQL](https://github.com/ivelum/djangoql), chosen per
  datasource.
* **Parametrised queries.** Every query is rendered as a Django template first,
  so it can take values from the report context (`pages > {{ min_pages }}`).
  A `sample_context` field supplies example values so a parametrised query can
  still be validated when it is saved.
* **Query shortcuts.** A model can declare `django_dsl_shortcuts = {"author":
  "author__name"}` and datasources may then use the short name.
* **Queries are validated on save.** The admin refuses a query that does not
  compile or that the database rejects, instead of producing a silently empty
  report.
* **Columns are templates.** A column either reads an attribute
  (`attr_name`, dot notation crosses relations: `author.name`) or renders a
  Django template snippet with `record`, `value` and `default` in its context —
  or both.
* **Footers and totals.** `display_totals` sums a column and renders
  `footer_template` with `value`, `count` and `error`.
* **Coordinated sorting.** Tables can sort independently, in a named group, or
  all together — clicking one header re-sorts every table on the page that has
  a column with the same label.
* **Default ordering** per table via `ColumnOrder` (any number of columns,
  ascending or descending).
* **"Everything else" tables.** A report element can be fed with *except
  catchall* data: every record from the base queryset that none of the report's
  datasources picked up.
* **Export.** A report renders to HTML, to a `.docx` (through
  [pypandoc](https://pypi.org/project/pypandoc/)) or to a
  [tablib](https://tablib.readthedocs.io/) `Dataset`/`Databook` (CSV, XLSX,
  …). Columns can be excluded from export or have their HTML stripped.
* **Cloning.** `Table.clone()` and `Report.clone()` — plus a *Clone* button on
  the admin change form — copy a definition (a table with its columns and sort
  order, a report with its elements) under a `(copy)` name.
* **Optional [grappelli](https://github.com/sehmaschine/django-grappelli)
  support**, detected at import time: inlines become drag-and-drop sortable
  when grappelli is installed, with no configuration.
* **Translatable**: all model verbose names, help texts and admin labels use
  `gettext`.

## Quickstart

Install Django Flexible Reports, with [uv](https://docs.astral.sh/uv/):

```
uv add django-flexible-reports
```

or with pip:

```
pip install django-flexible-reports
```

Add it (and `django_tables2`, which renders the tables) to your
`INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "django.contrib.admin",          # to edit reports
    "django.contrib.contenttypes",   # required: models point at ContentType
    ...
    "django_tables2",
    "flexible_reports",
]
```

Make sure the `request` context processor is enabled — the `{% flexible %}` tag
passes the surrounding template context to django-tables2, which needs
`request` in it:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        ...
        "OPTIONS": {
            "context_processors": [
                ...
                "django.template.context_processors.request",
            ],
        },
    },
]
```

Then run the migrations:

```
python manage.py migrate
```

**No URL patterns to include.** `flexible_reports.urls` exists but is empty —
the app ships no views of its own. You render reports from your own views. (Any
instructions telling you to `include(flexible_reports.urls)` are obsolete.)

Now define a report in the admin (*Flexible reports → Datasources / Tables /
Reports*) and render it from your own view:

```python
from django.shortcuts import render

from flexible_reports.models import Report

from .models import Book


def library_report(request):
    report = Report.objects.get(slug="library-report")
    # Required: every datasource narrows *this* queryset.
    report.set_base_queryset(Book.objects.select_related("author"))
    # Optional: values for parametrised queries, e.g. "pages > {{ min_pages }}".
    report.set_context({"min_pages": 300})
    return render(request, "library/report.html", {"report": report})
```

```django
{% load flexible_reports_tags %}
{% flexible report %}
```

That is the whole integration. Which tables the report has, which columns they
carry, how they are sorted and how the cells look is all read from the
database.

## Demo project

A complete, self-contained demo lives in [`demo/`](demo/) — two models, two
datasources (one per query language, one of them parametrised), a table with
six columns (dot notation, custom cell templates, totals) and a three-element
report including an *except catchall* table. It runs on SQLite, so no services
are needed:

```
make demo             # stock Django admin,       http://127.0.0.1:8000/
make demo-grappelli   # django-grappelli admin,   http://127.0.0.1:8001/
make demo-reset       # throw the demo database away
```

Log into the admin as **`admin` / `admin`**. See [`demo/README.md`](demo/README.md)
for a walkthrough of what the seeded report demonstrates.

## Optional system dependencies

* Exporting a report to `.docx` shells out to [pandoc](https://pandoc.org/)
  through `pypandoc`, so pandoc has to be installed on the machine
  (`apt install pandoc`, `brew install pandoc`).
* Writing `.xlsx` needs `openpyxl` (`pip install "tablib[xlsx]"`), which tablib
  does not pull in by default. CSV/JSON/YAML/TSV work out of the box.

HTML rendering needs nothing extra.

## Running Tests

```
uv sync --all-extras
uv run pytest
```

The test suite runs against PostgreSQL; see `tests/settings.py` (the
`POSTGRES_HOST` / `POSTGRES_PORT` environment variables are honoured), or start
one with the bundled `docker-compose.yml`.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development setup, how to run
the tests and the grappelli integration run, linting, and what CI checks.
The changelog is [`HISTORY.md`](HISTORY.md).

The manual under [`docs/`](docs/) is Markdown, built with
[MkDocs](https://www.mkdocs.org/) and the
[Material](https://squidfunk.github.io/mkdocs-material/) theme:

```
make docs         # live preview on http://127.0.0.1:8000/
make docs-build   # build with --strict, exactly as CI does
```

## License

MIT
