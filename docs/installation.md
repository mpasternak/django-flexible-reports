# Installation

## Requirements

|          |                                            |
|----------|--------------------------------------------|
| Python   | 3.10 -- 3.13                               |
| Django   | 5.2 LTS or 6.0 (6.0 needs Python 3.12+)    |
| Database | anything Django supports                   |

The following are installed automatically as dependencies:
[django-dsl][django-dsl], [djangoql-iplweb][djangoql-iplweb],
[django-tables2][django-tables2], [tablib][tablib], [lxml][lxml],
[pypandoc][pypandoc] and [bleach][bleach].

[django-dsl]: https://pypi.org/project/django-dsl/
[djangoql-iplweb]: https://pypi.org/project/djangoql-iplweb/
[django-tables2]: https://github.com/jieter/django-tables2
[tablib]: https://tablib.readthedocs.io/
[lxml]: https://lxml.de/
[pypandoc]: https://pypi.org/project/pypandoc/
[bleach]: https://pypi.org/project/bleach/

## Install the package

```console
$ pip install django-flexible-reports
```

Or, with [uv][uv]:

```console
$ uv add django-flexible-reports
```

[uv]: https://docs.astral.sh/uv/

## Configure the project

Add the app -- and `django_tables2`, which does the actual rendering -- to
`INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "django.contrib.admin",          # to edit report definitions
    "django.contrib.contenttypes",   # required: models point at ContentType
    ...
    "django_tables2",
    "flexible_reports",
]
```

`"flexible_reports.apps.FlexibleReportsConfig"` also works; it is the same
app config Django picks up by default.

Enable the `request` context processor. `{% flexible %}` hands the
surrounding template context to the django-tables2 adapter, which needs
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

Then create the tables:

```console
$ python manage.py migrate
```

## No URLconf changes

!!! note

    There is **nothing to add to your URLconf**. `flexible_reports.urls`
    exists but its `urlpatterns` is empty and `flexible_reports.views` is
    empty too -- the app ships no views. You render reports from your own
    views (see [Quickstart](quickstart.md)).

    Older versions of this documentation told you to write
    `url(r'^', include(flexible_reports_urls))`. That advice was doubly
    wrong: it achieved nothing, and `django.conf.urls.url` was removed in
    Django 4.0.

## Optional extras

grappelli
:   If [django-grappelli][django-grappelli] is installed,
    `flexible_reports.admin.helpers` detects it at import time and the
    `Column`, `ColumnOrder` and `ReportElement` inlines become drag-and-drop
    sortable. Nothing needs to be configured. Without grappelli the inlines
    simply show a numeric *Position* field.

pandoc
:   Exporting a report to `.docx` shells out to [pandoc][pandoc] through
    `pypandoc`, so the `pandoc` binary has to be present on the machine
    (`apt install pandoc`, `brew install pandoc`). HTML and tablib
    (XLSX/CSV/…) exports need nothing extra.

[django-grappelli]: https://github.com/sehmaschine/django-grappelli
[pandoc]: https://pandoc.org/
