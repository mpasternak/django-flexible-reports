# History

## 0.5.0 (2026-08-19)

* Added `Report.set_order_by(*fields)`, a third render-time setter alongside
  `set_base_queryset()` and `set_context()`. It overrides the ordering stored
  on every table of the report for one render, and takes ORM field names
  rather than the column labels `ColumnOrder` uses — so a report can be sorted
  by a field that no column displays, which the stored ordering cannot
  express. `ColumnOrder` is left untouched and keeps serving as the default;
  calling the setter with no arguments falls back to it.

## 0.4.2 (2026-08-07)

* Added support for Django 6.1. It joins 5.2 LTS and 6.0 in the tested matrix,
  on Python 3.12–3.14 (Django 6.1 requires Python 3.12+).

* Fixed validation of a `Column` whose *Attribute name* walks a relation in dot
  notation (`parent.title`) under Django 6.1. Resolving the far end of the
  relation went through the descriptor's `get_queryset()`, which in Django 6.1
  takes a mandatory `instance` argument and so cannot be called off the model
  class any more; every such column was rejected as invalid. The related model
  now comes from the relation metadata, which reads the same on 5.2, 6.0 and
  6.1.

## 0.4.1 (2026-07-23)

* Python 3.14 is supported and tested, against both Django 5.2 LTS and 6.0.

* PyPI metadata is fuller: real keywords instead of just the package name, and
  links to the documentation, repository, issue tracker and changelog rather
  than the homepage alone. `Development Status` moves from `3 - Alpha` to
  `5 - Production/Stable`.

* Internal: removed the last Python 2 leftovers (`__future__` imports, UTF-8
  encoding headers, `super(Class, self)`) and turned on ruff's `UP` (pyupgrade)
  ruleset, which had been off, so that they cannot creep back in. No runtime
  behaviour changed.

## 0.4.0 (2026-07-22)

* **Backwards incompatible:** the minimum supported Django is now 5.2 LTS.
  Tested against Django 5.2 and 6.0.

* The Polish translation now actually works when installed from PyPI. Django
  reads compiled `.mo` catalogues rather than the `.po` sources, and `*.mo` is
  gitignored, so every release up to and including 0.3.2 shipped the `.po`
  alone and the translation silently did nothing. Releases now compile the
  catalogues before building, and the build fails if the wheel ends up with
  fewer `.mo` files than `.po` files.

* The `example/` project, which could not start on any supported Django, is
  replaced by `demo/` -- a working project that runs against either the plain
  admin (`make demo`) or grappelli (`make demo-grappelli`) from one set of
  models and seed data.

* Documentation is rewritten and published to
  <https://mpasternak.github.io/django-flexible-reports/>. The previous
  `docs/readme.rst` included a `README.rst` that does not exist and
  rendered blank; the install instructions recommended `easy_install`.

  The manual is now built with [MkDocs](https://www.mkdocs.org/) and the
  [Material](https://squidfunk.github.io/mkdocs-material/) theme instead of
  Sphinx, and its sources are Markdown.

* Three migrations no longer import
  `django.contrib.postgres.fields.jsonb`. That import pulled in
  `psycopg2` at module load, so `migrate` failed on SQLite for anyone who
  had installed only the runtime dependencies.

* `Table` and `Report` can now be cloned from the admin, using a *Clone*
  button on the change form. Cloning a table copies its columns and its sort
  order; cloning a report copies its elements, which keep pointing at the same
  tables and datasources. The clone's name gets a translatable `(copy)`
  suffix.

  Both are also available programmatically as `Table.clone()` and
  `Report.clone()`. Neither modifies the source object.

  The button is verified to work with `grappelli`, which ships its own
  `admin/change_form.html`; a regression test guards it.

* Fix stale table headers. A cached table class was kept per `Table.pk` for
  the lifetime of the process and never invalidated, so editing a column's
  label -- or deleting a column -- only became visible after restarting
  Django. With several workers the page alternated between old and new
  headers depending on which worker answered.

  The cache is gone. Compiled column templates are cached instead, keyed by
  the template source so no invalidation is needed, which more than pays the
  removal back: rendering a 500-row table is ~1.25x faster than before, since
  `TemplateColumn` used to recompile its template for every single cell.

## 0.3.2 (2026-06-03)

* Switch the DjangoQL dependency from upstream `djangoql` to the
  `djangoql-iplweb` fork (`>=0.20`). The fork keeps the `djangoql` import
  name unchanged, so no code changes are required, and it adds i18n support for
  parser/lexer/schema error messages (including a Polish translation).

## 0.3.1 (2026-05-31)

* `Datasource` gained an optional `sample_context` field holding example
  values for a query's template parameters, used to validate a parametrised
  query on save (both `dsl` and `DjangoQL` backends). It is nullable and
  must be a JSON object.
* Fix an admin 500 when clearing *Sample parameters* — the `sample_context`
  JSONField is now nullable.
* Don't HTML-escape query parameters when rendering `DjangoQL` queries, so
  values containing `<`, `&` or `"` are no longer corrupted. The
  `django-dsl` backend received the same fix in django-dsl 0.1.14.
* Fix the except-catchall element lookup (key off `ContentType.model`) so the
  "everything except" table renders its rows instead of being silently empty;
  the caught querysets are OR-ed into a single exclude.
* Escape the datasource query shown in the admin changelist.
* Chain `ValidationError` from the original backend error for clearer
  diagnostics.

## 0.3.0 (2026-05-31)

* `Datasource` gained a `query_language` field and can now interpret its
  query with either `django-dsl` (default) or
  [DjangoQL](https://github.com/ivelum/djangoql). Query backends are
  pluggable (`flexible_reports.query_backends`). The django_tables2 adapter
  now consumes a filtered queryset from each datasource instead of a raw `Q`
  object. Existing datasources keep working unchanged (default `dsl`).

## 0.2.12 (2026-04-19)

* Fix `DeprecationWarning: Pickle, copy, and deepcopy support will be
  removed from itertools in Python 3.14` raised when instantiating a
  `Table` with columns using `CounterMixin`. The mixin now keeps
  the counter as a plain `int` instead of `itertools.count` so
  that columns stored in `Table.base_columns` remain deep-copyable
  on Python 3.14.
* `tests.settings.DATABASES['default']['PORT']` now respects the
  `POSTGRES_PORT` environment variable (default: `5432`).

## 0.2.10 (2022-07-07)

* Drop support for Django 2.2 and below,
* Drop support for Python 3.7,
* Python 3.10 support,
* Django 3.2 support,
* enable GitHub Actions,
* remove Travis-CI config.

## 0.1.0 (2017-07-20)

* First release on PyPI.
