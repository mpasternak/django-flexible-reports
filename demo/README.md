# django-flexible-reports demo project

A tiny, self-contained Django project that shows `django-flexible-reports`
doing its job: a report whose tables, columns, formatting and sorting live in
the database and are edited through the admin.

It runs in two flavours from **one** project and **one** database:

| Flavour   | Settings module          | Admin skin                | Suggested port |
|-----------|--------------------------|---------------------------|----------------|
| Django    | `demo.settings_django`   | stock `django.contrib.admin` | 8000        |
| Grappelli | `demo.settings_grappelli`| [django-grappelli]        | 8001           |

[django-grappelli]: https://github.com/sehmaschine/django-grappelli

Everything uses SQLite (`demo/db.sqlite3`), so no services are needed.

## Quick start

From the repository root:

```bash
make demo             # plain Django admin, http://127.0.0.1:8000/
make demo-grappelli   # grappelli,          http://127.0.0.1:8001/
make demo-reset       # throw the demo database away
```

Both targets run `migrate`, then `seed_demo`, then `runserver`. Log into the
admin as **`admin` / `admin`**.

Without `make`:

```bash
python demo/manage.py migrate
python demo/manage.py seed_demo
python demo/manage.py runserver 127.0.0.1:8000

# or, with grappelli installed (it is not a dependency of this package):
pip install django-grappelli
python demo/manage.py migrate    --settings=demo.settings_grappelli
python demo/manage.py seed_demo  --settings=demo.settings_grappelli
python demo/manage.py runserver 127.0.0.1:8001 --settings=demo.settings_grappelli
```

`demo/manage.py` puts the repository root on `sys.path` itself, so the demo
always exercises the working copy of `flexible_reports`, not a release
installed in the environment.

## What you are looking at

`demoapp` defines two models — `Author` and `Book(title, author, year, pages,
price)`. `manage.py seed_demo` fills them with ten books and then builds a
complete report definition. Everything it creates is visible and editable in
the admin under *Flexible reports*.

**Datasources** (what goes into a table). Both supported query languages are
demonstrated:

* *Long books* — **DjangoQL**, `pages > {{ min_pages }}`. The query is a Django
  template, rendered with the context the view passes to
  `Report.set_context()`. `sample_context` holds an example value so the query
  can be validated when the datasource is saved.
* *Everything by Ursula K. Le Guin* — **django-dsl**, `author = "Ursula K. Le
  Guin"`. `author` is not a field on `Book`; it is a shorthand declared as
  `Book.django_dsl_shortcuts = {"author": "author__name", ...}`, which the
  library picks up automatically.

**Table + columns** (how it is rendered). One `Table` with six `Column`s,
reused by all three report elements:

* `Nr` — no `attr_name` at all, just a template using django-tables2's
  `{{ row_counter }}`; not sortable, but shows the row count in the footer via
  `display_totals` + `{{ count }}`.
* `Title` — a custom cell template mixing the resolved `{{ value }}` with
  another attribute of `{{ record }}`.
* `Author`, `Country` — **dot notation** (`author.name`, `author.country`),
  i.e. the column reaches across the foreign key.
* `Year` — plain sortable column.
* `Price` — `display_totals` over a numeric column; the footer template gets
  the sum in `{{ value }}`.

Two `ColumnOrder` rows give the table its default sorting: year descending,
then title ascending. The table's sort option is *sort with other tables*, so
clicking a header re-sorts all three tables at once.

**Report** (the glue). Three `ReportElement`s:

1. *Long books* — from the DjangoQL datasource,
2. *Everything by Ursula K. Le Guin* — from the django-dsl datasource,
3. *Everything else* — `data_from = except catchall`: whatever the datasources
   above did **not** catch. No datasource, just a base model.

The report's `template` field is left at the shipped default
(`flexible_reports/templates/flexible_reports/report.html`) — edit it in the
admin to change the layout.

## How the page renders the report

`demoapp/views.py` is the whole story:

```python
report = Report.objects.get(slug=settings.DEMO_REPORT_SLUG)
report.set_base_queryset(Book.objects.select_related("author"))   # required
report.set_context({"min_pages": settings.DEMO_MIN_PAGES})        # optional
return render(request, "demo/index.html", {"report": report})
```

and `demo/templates/demo/index.html` does:

```django
{% load flexible_reports_tags %}
{% flexible report %}
```

`set_base_queryset()` is mandatory: datasources narrow *that* queryset, so
nothing outside of it can ever appear in the report. The
`django.template.context_processors.request` context processor must be
enabled — the tag hands the surrounding template context to the
django-tables2 adapter, which needs `request` in it.

## Notes on the grappelli flavour

`demo/settings_grappelli.py` differs from the plain one in two lines, both of
which matter:

1. `grappelli` is prepended to `INSTALLED_APPS`, **before**
   `django.contrib.admin`. Both apps ship `admin/*.html`; with the app-dirs
   template loader the first one wins, so putting grappelli last silently
   gives you the vanilla admin back.
2. `demo/urls.py` routes `grappelli.urls` (it checks
   `apps.is_installed("grappelli")`, which is why one URLconf serves both
   flavours). Without it, related-object lookups and autocompletes 404.

With grappelli installed, `flexible_reports.admin.helpers` automatically
switches to `GrappelliSortableHiddenMixin`, so column and report-element
inlines become drag-and-drop reorderable with no extra configuration. The
"Clone" button on the `Table` and `Report` change forms works in both
flavours.

## Re-seeding

`seed_demo` is idempotent. Authors and books are upserted; the datasources,
the table, its columns and the report are deleted and rebuilt. Break the demo
report in the admin, re-run `seed_demo`, and you are back to a known state.
