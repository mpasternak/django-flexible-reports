# Django Flexible Reports

[![PyPI](https://badge.fury.io/py/django-flexible-reports.svg)](https://badge.fury.io/py/django-flexible-reports)
[![Tests](https://github.com/mpasternak/django-flexible-reports/actions/workflows/tests.yml/badge.svg)](https://github.com/mpasternak/django-flexible-reports/actions)
[![Coverage](https://coveralls.io/repos/github/mpasternak/django-flexible-reports/badge.svg?branch=master)](https://coveralls.io/github/mpasternak/django-flexible-reports?branch=master)

A framework for report generation in Django

## Supported Versions

|              | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|--------------|:-----------:|:-----------:|:-----------:|:-----------:|
| Django 4.2   | ✔           | ✔           | ✔           | ✔           |
| Django 5.0   | ✔           | ✔           | ✔           | ✔           |
| Django 5.1   | ✔           | ✔           | ✔           | ✔           |

## Documentation

The full documentation is at https://django-flexible-reports.readthedocs.io.

## Quickstart

Install Django Flexible Reports:

```
pip install django-flexible-reports
```

Add it to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = (
    ...
    'flexible_reports.apps.FlexibleReportsConfig',
    ...
)
```

Add Django Flexible Reports's URL patterns:

```python
from flexible_reports import urls as flexible_reports_urls

urlpatterns = [
    ...
    url(r'^', include(flexible_reports_urls)),
    ...
]
```

## Features

* TODO

## Running Tests

```
uv sync --all-extras
uv run pytest
```

## License

MIT
