# The demo project

The source tree ships a small, self-contained Django project in `demo/` that
exercises everything described in this manual. It runs on SQLite, so no
services are needed.

```console
$ make demo             # stock Django admin,     http://127.0.0.1:8000/
$ make demo-grappelli   # django-grappelli admin, http://127.0.0.1:8001/
$ make demo-reset       # throw the demo database away
```

Each target runs `migrate`, then `seed_demo`, then `runserver`. Log into the
admin as **admin / admin**.

Without `make`:

```console
$ python demo/manage.py migrate
$ python demo/manage.py seed_demo
$ python demo/manage.py runserver 127.0.0.1:8000
```

`demo/manage.py` puts the repository root on `sys.path` itself, so the demo
always exercises the working copy of `flexible_reports`, not a release
installed in the environment.

Both flavours share one project and one database; they differ only in the
settings module (`demo.settings_django` vs `demo.settings_grappelli`).

## What the demo shows

`demoapp` defines `Author` and `Book(title, author, year, pages, price)`
and `manage.py seed_demo` fills them with ten books, then builds a complete
report definition -- all of it visible and editable in the admin under
*Flexible reports*.

**Two datasources**, one per query language:

* *Long books* -- DjangoQL, `pages > {{ min_pages }}`: a parametrised query
  whose value comes from `Report.set_context()`, with `sample_context`
  supplying an example for save-time validation.
* *Everything by Ursula K. Le Guin* -- django-dsl,
  `author = "Ursula K. Le Guin"`, where `author` is a shortcut declared as
  `Book.django_dsl_shortcuts`.

**One table with six columns**, reused by all three report elements: a
template-only column using `row_counter`, a column mixing `value` with
`record`, two dot-notation columns crossing the foreign key, a plain sortable
column and a numeric column with totals. Two `ColumnOrder` rows give it a
default sort (year descending, then title). The sort option is *sort with other
tables*, so clicking a header re-sorts all three tables at once.

**A report with three elements**, the last of which uses *except catchall* --
everything the two datasources did not pick up.

The rendering side is two files:

```python
# demo/demoapp/views.py
report = Report.objects.get(slug=settings.DEMO_REPORT_SLUG)
report.set_base_queryset(Book.objects.select_related("author"))
report.set_context({"min_pages": settings.DEMO_MIN_PAGES})
return render(request, "demo/index.html", {"report": report})
```

```django
{# demo/templates/demo/index.html #}
{% load flexible_reports_tags %}
{% flexible report %}
```

`seed_demo` is idempotent: sample data is upserted and the report definition
is deleted and rebuilt. Break the report in the admin, re-run the command, and
you are back to a known state.

See `demo/README.md` in the source tree for the full walkthrough, including
the two lines that make the grappelli flavour work.
