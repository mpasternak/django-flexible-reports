# DjangoQL Query Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a `Datasource` interpret its query with either `django-dsl` (current default) or `DjangoQL`, selected per-datasource, with template parametrisation and save-time validation preserved for both.

**Architecture:** Introduce a small pluggable "query backend" registry. Each backend renders the stored query as a Django template and turns it into a *filtered queryset* (`filter_queryset`) and validates it (`validate`). The `Datasource` gains a `query_language` discriminator (default `dsl`, so existing rows are unchanged). The django_tables2 adapter stops consuming a raw `Q` object and instead asks the datasource for a filtered queryset; the catchall/except-catchall logic switches from OR-composing `Q` objects to excluding `pk__in` per queryset (semantically identical for the single-model case, more correct for multi-model).

**Tech Stack:** Django 4.2+, `django-dsl`, `DjangoQL`, `django-tables2`, pytest / pytest-django, uv.

---

## Prerequisites (read before starting)

- **Postgres must be running** — `tests/settings.py` uses the postgres backend. Start it with `docker-compose up -d` from the repo root if it is not already up.
- Run all commands from the repo root: `/Users/mpasternak/Programowanie/django-flexible-reports`.
- Tests are run with `.venv/bin/pytest <path>`. `addopts = "-s --ds=tests.settings"` is configured in `pyproject.toml`, so no `--ds` flag is needed.
- `manage.py` already defaults `DJANGO_SETTINGS_MODULE=tests.settings`.

## Key design facts (verified against the code/libraries)

- `django_dsl.compiler.compile(query, shortcuts, context)` renders `query` as a Django template with `context`, then returns a `django.db.models.Q`. Empty/whitespace render breaks parsing (so templated queries must use `|default:`).
- `djangoql.queryset.apply_search(queryset, search, schema=None)` parses + schema-validates + returns a **filtered queryset**. There is no public API returning a `Q`. It does **not** render templates — we render before calling it.
- `djangoql.exceptions.DjangoQLError` is the common base of `DjangoQLParserError`, `DjangoQLLexerError`, and `DjangoQLSchemaError` — catching it covers syntax and unknown-field/type errors.
- Existing model field `Datasource.dsl_query` is a `DjangoDSLField` (a `TextField` whose only extra behaviour is a hard-wired DSL validator). That validator would reject valid DjangoQL, so the field must become a plain `TextField` and validation must move to `Datasource.clean()` (which knows both `query_language` and the model).

## File Structure

- **Create** `flexible_reports/query_backends.py` — backend registry + `DSLQueryBackend` + `DjangoQLQueryBackend` + constants (`DSL`, `DJANGOQL`, `QUERY_LANGUAGE_CHOICES`, `get_backend`). Single responsibility: turn a query string into a filtered queryset / validate it.
- **Create** `flexible_reports/migrations/0012_add_query_language.py` — add `query_language`, retype `dsl_query` to `TextField`.
- **Modify** `flexible_reports/models/datasource.py` — add `query_language`, retype `dsl_query`, add `get_backend()`/`filter_queryset()`/`clean()`, route `get_filter()` through the backend.
- **Modify** `flexible_reports/admin/datasource.py` — drop the DSL-specific `clean()` (validation now lives on the model), expose `query_language` in the form and `list_display`.
- **Modify** `flexible_reports/adapters/django_tables2.py` — `_report()` consumes `filter_queryset()` and rebuilds catchall on querysets.
- **Modify** `pyproject.toml` — add `djangoql` runtime dependency.
- **Create** `test_app/tests/test_query_backends.py` — unit tests for both backends.
- **Modify** `test_app/tests/test_models/test_datasource.py` — add model-level validation + filter tests.
- **Modify** `test_app/tests/test_admin/test_datasource.py` — rewrite form tests for both languages.
- **Modify** `test_app/tests/test_adapters.py` — add a DjangoQL catchall test (DSL one is the regression guard).
- **Modify** `docs/usage.rst` and `HISTORY.rst` — document the feature.

---

### Task 1: Add the DjangoQL runtime dependency

**Files:**
- Modify: `pyproject.toml` (dependencies array, lines ~27-35)

- [ ] **Step 1: Add the dependency**

Edit `pyproject.toml` so the `dependencies` array gains the `djangoql` line (keep the others unchanged):

```toml
dependencies = [
    "Django>=4.2",
    "django-dsl>=0.1.12",
    "djangoql>=0.18",
    "django-tables2>=1.16.0",
    "tablib>=0.11.5",
    "lxml>=3.8.0",
    "pypandoc>=1.4",
    "bleach>=2.1.1",
]
```

- [ ] **Step 2: Sync the environment**

Run: `uv sync --extra test`
Expected: resolves and installs `djangoql` into `.venv` (plus the existing test extras).

- [ ] **Step 3: Verify the import works**

Run: `.venv/bin/python -c "import djangoql, djangoql.queryset, djangoql.exceptions; print('djangoql ok')"`
Expected: prints `djangoql ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add djangoql dependency

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Query backend registry (DSL + DjangoQL)

**Files:**
- Create: `flexible_reports/query_backends.py`
- Test: `test_app/tests/test_query_backends.py`

- [ ] **Step 1: Write the failing tests**

Create `test_app/tests/test_query_backends.py`:

```python
# -*- encoding: utf-8 -*-
import pytest
from django.core.exceptions import ValidationError

from flexible_reports.query_backends import (
    DjangoQLQueryBackend,
    DSLQueryBackend,
    get_backend,
)
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_dsl_filter_queryset():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    qs = DSLQueryBackend().filter_queryset(MyTestFoo.objects.all(), "i = 5")
    assert sorted(o.i for o in qs) == [5]


@pytest.mark.django_db
def test_djangoql_filter_queryset():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    qs = DjangoQLQueryBackend().filter_queryset(MyTestFoo.objects.all(), "i = 5")
    assert sorted(o.i for o in qs) == [5]


@pytest.mark.django_db
def test_djangoql_filter_queryset_uses_template_context():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    qs = DjangoQLQueryBackend().filter_queryset(
        MyTestFoo.objects.all(), "i = {{ value }}", context={"value": 7}
    )
    assert sorted(o.i for o in qs) == [7]


@pytest.mark.django_db
def test_dsl_validate_unknown_field_raises():
    with pytest.raises(ValidationError):
        DSLQueryBackend().validate("nope > 1", MyTestFoo)


@pytest.mark.django_db
def test_djangoql_validate_unknown_field_raises():
    with pytest.raises(ValidationError):
        DjangoQLQueryBackend().validate("nope = 1", MyTestFoo)


def test_djangoql_validate_empty_raises():
    with pytest.raises(ValidationError):
        DjangoQLQueryBackend().validate("   ", MyTestFoo)


def test_djangoql_get_filter_not_supported():
    with pytest.raises(NotImplementedError):
        DjangoQLQueryBackend().get_filter("i = 5", MyTestFoo)


def test_get_backend_returns_expected_types():
    assert isinstance(get_backend("dsl"), DSLQueryBackend)
    assert isinstance(get_backend("djangoql"), DjangoQLQueryBackend)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest test_app/tests/test_query_backends.py -v`
Expected: collection/import error — `ModuleNotFoundError: No module named 'flexible_reports.query_backends'`

- [ ] **Step 3: Create the backend module**

Create `flexible_reports/query_backends.py`:

```python
# -*- encoding: utf-8 -*-
"""Pluggable query backends for :class:`~flexible_reports.models.datasource.Datasource`.

Each backend knows how to:

* turn the textual query stored on a datasource into a *filtered queryset*
  (``filter_queryset``), and
* validate that query at save time (``validate``).

The query string is always rendered as a Django template first, so reports can
parametrise queries with values from the report context.
"""
from django.core.exceptions import ValidationError
from django.template import Context
from django.template.base import Template

try:
    from django.utils.translation import gettext_lazy as _
except ImportError:  # Django < 4
    from django.utils.translation import ugettext_lazy as _

from . import utils

DSL = "dsl"
DJANGOQL = "djangoql"

QUERY_LANGUAGE_CHOICES = [
    (DSL, "django-dsl"),
    (DJANGOQL, "DjangoQL"),
]


def _check_not_empty(query):
    if not query or not query.strip():
        raise ValidationError(
            {"dsl_query": [ValidationError(_("Query must not be an empty string"))]}
        )


class DSLQueryBackend:
    """``django-dsl`` backend (the historical default)."""

    name = DSL

    def get_filter(self, query, model, context=None):
        """Return a ``Q`` object for ``query`` (django-dsl renders templates itself)."""
        from django_dsl import compiler

        return compiler.compile(
            query, shortcuts=utils.get_shortcuts(model), context=context or {}
        )

    def filter_queryset(self, base_queryset, query, context=None):
        return base_queryset.filter(
            self.get_filter(query, base_queryset.model, context)
        )

    def validate(self, query, model):
        from django_dsl import compiler, exceptions

        _check_not_empty(query)
        try:
            compiled = compiler.compile(query, shortcuts=utils.get_shortcuts(model))
        except exceptions.CompileException as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _("DSL compilation failed (%(error)s)"),
                            params={"error": e},
                        )
                    ]
                }
            )
        try:
            model.objects.filter(compiled).first()
        except Exception as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _(
                                "An error occured while trying to run the actual "
                                "database query (%(error)s)"
                            ),
                            params={"error": e},
                        )
                    ]
                }
            )


class DjangoQLQueryBackend:
    """`DjangoQL <https://github.com/ivelum/djangoql>`_ backend."""

    name = DJANGOQL

    def _render(self, query, context):
        return Template(query).render(Context(context or {}))

    def get_filter(self, query, model, context=None):
        raise NotImplementedError(
            "The DjangoQL backend produces a filtered queryset, not a Q object; "
            "use filter_queryset() instead of get_filter()."
        )

    def filter_queryset(self, base_queryset, query, context=None):
        from djangoql.queryset import apply_search

        return apply_search(base_queryset, self._render(query, context))

    def validate(self, query, model):
        from djangoql.exceptions import DjangoQLError
        from djangoql.queryset import apply_search

        _check_not_empty(query)
        rendered = self._render(query, {})
        try:
            apply_search(model.objects.all(), rendered).first()
        except DjangoQLError as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _("DjangoQL query is invalid (%(error)s)"),
                            params={"error": e},
                        )
                    ]
                }
            )
        except Exception as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _(
                                "An error occured while trying to run the actual "
                                "database query (%(error)s)"
                            ),
                            params={"error": e},
                        )
                    ]
                }
            )


BACKENDS = {
    DSL: DSLQueryBackend(),
    DJANGOQL: DjangoQLQueryBackend(),
}


def get_backend(name):
    return BACKENDS[name]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest test_app/tests/test_query_backends.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add flexible_reports/query_backends.py test_app/tests/test_query_backends.py
git commit -m "feat: add pluggable DSL/DjangoQL query backends

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Datasource model — query_language field, backend routing, migration

**Files:**
- Modify: `flexible_reports/models/datasource.py` (entire file)
- Create: `flexible_reports/migrations/0012_add_query_language.py`
- Test: `test_app/tests/test_models/test_datasource.py`

- [ ] **Step 1: Write the failing tests**

Append to `test_app/tests/test_models/test_datasource.py` (keep the two existing tests intact):

```python
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_datasource_filter_queryset_dsl():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="dsl",
        dsl_query="i = 5",
    )
    assert sorted(o.i for o in d.filter_queryset(MyTestFoo.objects.all())) == [5]


@pytest.mark.django_db
def test_datasource_filter_queryset_djangoql():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="djangoql",
        dsl_query="i = 5",
    )
    assert sorted(o.i for o in d.filter_queryset(MyTestFoo.objects.all())) == [5]


@pytest.mark.django_db
def test_datasource_clean_djangoql_ok():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="djangoql",
        dsl_query="i = 5",
    )
    d.clean()  # must not raise


@pytest.mark.django_db
def test_datasource_clean_djangoql_unknown_field_raises():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="djangoql",
        dsl_query="nope = 1",
    )
    with pytest.raises(ValidationError):
        d.clean()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest test_app/tests/test_models/test_datasource.py -v`
Expected: FAIL — `TypeError`/`FieldError` on `query_language` (field does not exist yet) and/or `AttributeError: 'Datasource' object has no attribute 'filter_queryset'`.

- [ ] **Step 3: Rewrite the model**

Replace the entire contents of `flexible_reports/models/datasource.py` with:

```python
# -*- encoding: utf-8 -*-
from django.db import models

try:
    from django.utils.translation import gettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

from ..query_backends import DSL, QUERY_LANGUAGE_CHOICES, get_backend
from .behaviors import Labelled, WithBaseModel


class Datasource(Labelled, WithBaseModel):
    """Datasource gets data from the database.

    It narrows ``self.base_model.objects.all()`` using the query stored in
    ``dsl_query``, interpreted according to ``query_language`` (django-dsl or
    DjangoQL).
    """

    query_language = models.CharField(
        max_length=16,
        choices=QUERY_LANGUAGE_CHOICES,
        default=DSL,
        verbose_name=_("Query language"),
    )

    dsl_query = models.TextField(verbose_name=_("Query"))

    distinct = models.BooleanField(
        default=True,
        verbose_name=_("Distinct"),
        help_text=_("Output only distinct records"),
    )

    class Meta:
        verbose_name = _("Datasource")
        verbose_name_plural = _("Datasources")
        ordering = ("label",)

    def get_model(self):
        return self.base_model.model_class()

    def get_shortcuts(self):
        return getattr(self.get_model(), "django_dsl_shortcuts", {})

    def get_backend(self):
        return get_backend(self.query_language)

    def get_filter(self, context=None):
        """Return a ``Q`` object for the query.

        Only the django-dsl backend can produce a ``Q``; the DjangoQL backend
        raises ``NotImplementedError`` (use :meth:`filter_queryset` instead).
        """
        return self.get_backend().get_filter(self.dsl_query, self.get_model(), context)

    def filter_queryset(self, base_queryset, context=None):
        """Return ``base_queryset`` narrowed by this datasource's query."""
        return self.get_backend().filter_queryset(
            base_queryset, self.dsl_query, context
        )

    def clean(self):
        if self.base_model_id is None:
            return
        self.get_backend().validate(self.dsl_query, self.get_model())
```

- [ ] **Step 4: Create the migration**

Create `flexible_reports/migrations/0012_add_query_language.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "flexible_reports",
            "0011_alter_reportelement_options_alter_column_attrs_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="datasource",
            name="query_language",
            field=models.CharField(
                choices=[("dsl", "django-dsl"), ("djangoql", "DjangoQL")],
                default="dsl",
                max_length=16,
                verbose_name="Query language",
            ),
        ),
        migrations.AlterField(
            model_name="datasource",
            name="dsl_query",
            field=models.TextField(verbose_name="Query"),
        ),
    ]
```

- [ ] **Step 5: Verify there is no migration drift**

Run: `.venv/bin/python manage.py makemigrations --check --dry-run flexible_reports`
Expected: `No changes detected in app 'flexible_reports'`
(If it reports changes, reconcile the hand-written migration with the model — usually a `choices`/`verbose_name` mismatch — then re-run.)

- [ ] **Step 6: Run the datasource tests (new + existing) to verify they pass**

Run: `.venv/bin/pytest test_app/tests/test_models/test_datasource.py -v`
Expected: all PASS, including the pre-existing `test_datasource` (`str(d.get_filter()) == "(AND: ('i', 5))"`) and `test_datasource_foreign`.

- [ ] **Step 7: Commit**

```bash
git add flexible_reports/models/datasource.py flexible_reports/migrations/0012_add_query_language.py test_app/tests/test_models/test_datasource.py
git commit -m "feat: add query_language to Datasource and route through backends

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Admin — expose query_language, move validation to the model

**Files:**
- Modify: `flexible_reports/admin/datasource.py` (entire file)
- Test: `test_app/tests/test_admin/test_datasource.py` (entire file)

- [ ] **Step 1: Rewrite the failing tests**

Replace the entire contents of `test_app/tests/test_admin/test_datasource.py` with:

```python
# -*- encoding: utf-8 -*-
import pytest
from django.contrib.contenttypes.models import ContentType

from flexible_reports.admin.datasource import DatasourceForm
from test_app.models import MyTestFoo


def _data(**over):
    data = {
        "label": "ds",
        "base_model": ContentType.objects.get_for_model(MyTestFoo).pk,
        "query_language": "dsl",
        "dsl_query": "i = 5",
        "distinct": True,
    }
    data.update(over)
    return data


@pytest.mark.django_db
def test_datasource_form_has_query_language():
    assert "query_language" in DatasourceForm().fields


@pytest.mark.django_db
def test_datasource_form_valid_dsl():
    form = DatasourceForm(data=_data())
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_datasource_form_invalid_dsl_db_error():
    form = DatasourceForm(data=_data(dsl_query="x > 100"))
    assert not form.is_valid()
    assert "dsl_query" in form.errors


@pytest.mark.django_db
def test_datasource_form_valid_djangoql():
    form = DatasourceForm(data=_data(query_language="djangoql", dsl_query="i = 5"))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_datasource_form_invalid_djangoql_unknown_field():
    form = DatasourceForm(data=_data(query_language="djangoql", dsl_query="nope = 1"))
    assert not form.is_valid()
    assert "dsl_query" in form.errors
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest test_app/tests/test_admin/test_datasource.py -v`
Expected: FAIL — `test_datasource_form_has_query_language` fails (field not in form) and the DjangoQL cases error/fail because the form still runs the DSL-only `clean()`.

- [ ] **Step 3: Rewrite the admin module**

Replace the entire contents of `flexible_reports/admin/datasource.py` with:

```python
# -*- encoding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe

try:
    from django.utils.translation import gettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

from ..models.datasource import Datasource
from .helpers import BiggerTextarea, SmallerTextarea


class DatasourceForm(forms.ModelForm):
    # Validation lives on Datasource.clean(), which dispatches to the query
    # backend selected by ``query_language``; the ModelForm runs it for us.
    class Meta:
        model = Datasource
        fields = ["label", "base_model", "query_language", "dsl_query", "distinct"]
        widgets = {"label": SmallerTextarea, "dsl_query": BiggerTextarea}


@admin.register(Datasource)
class DatasourceAdmin(admin.ModelAdmin):
    list_display = ["label", "base_model", "query_language", "dsl_query_fmt"]
    form = DatasourceForm

    def dsl_query_fmt(self, obj):
        return mark_safe(f"<pre>{ obj.dsl_query }</pre>")

    dsl_query_fmt.short_description = _("Query")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest test_app/tests/test_admin/ -v`
Expected: all PASS (datasource form tests + the unchanged `test_admin/test_report.py`).

- [ ] **Step 5: Commit**

```bash
git add flexible_reports/admin/datasource.py test_app/tests/test_admin/test_datasource.py
git commit -m "feat: expose query_language in admin, validate via model clean

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Adapter — consume filter_queryset, rebuild catchall on querysets

**Files:**
- Modify: `flexible_reports/adapters/django_tables2.py` (`_report()`, lines ~184-231)
- Test: `test_app/tests/test_adapters.py`

- [ ] **Step 1: Write the failing test**

Append to `test_app/tests/test_adapters.py`:

```python
@pytest.mark.django_db
def test_catchall_except_catchall_djangoql(rf):
    for a in range(1, 6):
        baker.make(MyTestFoo, i=a)

    mtf = ContentType.objects.get_for_model(MyTestFoo)

    r = baker.make(Report)
    t = baker.make(Table, base_model=mtf)
    baker.make(Column, parent=t)

    ds = baker.make(
        Datasource, base_model=mtf, query_language="djangoql", dsl_query="i < 3"
    )
    baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )

    ds = baker.make(
        Datasource, base_model=mtf, query_language="djangoql", dsl_query="i > 3"
    )
    baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )

    baker.make(
        ReportElement,
        table=t,
        parent=r,
        datasource=None,
        base_model=mtf,
        data_from=DATA_FROM_EXCEPT_CATCHALL,
    )

    r.set_base_queryset(MyTestFoo.objects.all())

    res = django_tables2._report(r, {"request": None})
    assert res["except_catchall"]["test_app_mytestfoo"].count() == 1
    assert res["except_catchall"]["test_app_mytestfoo"][0].i == 3
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest test_app/tests/test_adapters.py::test_catchall_except_catchall_djangoql -v`
Expected: FAIL — `_report()` still calls `datasource.get_filter()`, which raises `NotImplementedError` for the DjangoQL backend.

- [ ] **Step 3: Update the datasource branch of `_report()`**

In `flexible_reports/adapters/django_tables2.py`, replace this block (currently lines ~185-198):

```python
        if elem.data_from == DATA_FROM_DATASOURCE:
            datasource = elem.datasource
            filter = datasource.get_filter(context=report.context)
            object_list = report.base_queryset.filter(filter)

            ds_key = "%s_%s" % (
                datasource.base_model.app_label,
                datasource.base_model.model,
            )

            render_context["catchall"][ds_key].append(filter)

            if datasource.distinct:
                object_list = object_list.distinct()
```

with:

```python
        if elem.data_from == DATA_FROM_DATASOURCE:
            datasource = elem.datasource
            object_list = datasource.filter_queryset(
                report.base_queryset, context=report.context
            )

            ds_key = "%s_%s" % (
                datasource.base_model.app_label,
                datasource.base_model.model,
            )

            render_context["catchall"][ds_key].append(object_list)

            if datasource.distinct:
                object_list = object_list.distinct()
```

- [ ] **Step 4: Update the except-catchall fill of `_report()`**

In the same file, replace this block (currently lines ~215-231):

```python
    # Fill except-catchall
    except_catchall = report.base_queryset.all()
    q = None
    for key, filters in render_context["catchall"].items():
        if not filters:
            continue

        if q is None:
            q = filters[0]
        for filter in filters[1:]:
            q |= filter

        except_catchall = except_catchall.exclude(
            pk__in=report.base_queryset.filter(q).values_list("pk", flat=True)
        )

        render_context["except_catchall"][key] = except_catchall
```

with:

```python
    # Fill except-catchall.
    # ``catchall`` now holds the already-filtered querysets produced by each
    # datasource (instead of raw Q objects), so we exclude their primary keys
    # one queryset at a time. Excluding A then B is equivalent to excluding
    # A | B, which matches the previous OR-of-Q behaviour for a single model
    # and is well-defined when several models are involved.
    except_catchall = report.base_queryset.all()
    for key, querysets in render_context["catchall"].items():
        if not querysets:
            continue

        for object_list in querysets:
            except_catchall = except_catchall.exclude(
                pk__in=object_list.values_list("pk", flat=True)
            )

        render_context["except_catchall"][key] = except_catchall
```

- [ ] **Step 5: Run the adapter tests to verify they pass**

Run: `.venv/bin/pytest test_app/tests/test_adapters.py -v`
Expected: all PASS — the new `test_catchall_except_catchall_djangoql` plus the regression guards `test_catchall_except_catchall` (DSL), `test_report`, and `test_sum_text_field`.

- [ ] **Step 6: Commit**

```bash
git add flexible_reports/adapters/django_tables2.py test_app/tests/test_adapters.py
git commit -m "refactor: adapter consumes filtered querysets, catchall by pk

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Documentation and changelog

**Files:**
- Modify: `docs/usage.rst` (append a section)
- Modify: `HISTORY.rst` (add an entry at the top of the history list)

- [ ] **Step 1: Append the usage section**

Append to the end of `docs/usage.rst`:

```rst

Query languages
---------------

A ``Datasource`` interprets its query according to the ``query_language``
field:

* ``dsl`` (default) — `django-dsl`_ expressions, e.g.
  ``i > 0 AND i < 10``.
* ``djangoql`` — `DjangoQL`_ expressions, e.g. ``i > 0 and i < 10``.

In both cases the query is first rendered as a Django template, so it can be
parametrised from the report context, e.g. ``i = {{ value|default:0 }}``. Use a
``|default:`` filter so the query still validates when it is saved with an empty
context.

Existing datasources are unaffected: the column added by the migration defaults
to ``dsl``.

.. _django-dsl: https://pypi.org/project/django-dsl/
.. _DjangoQL: https://github.com/ivelum/djangoql
```

- [ ] **Step 2: Add the changelog entry**

In `HISTORY.rst`, insert a new entry directly **above** the `0.2.12 (2026-04-19)` block (keep the `History` / `-------` header at the very top):

```rst
0.3.0 (unreleased)
++++++++++++++++++

* ``Datasource`` gained a ``query_language`` field and can now interpret its
  query with either ``django-dsl`` (default) or `DjangoQL`_. Query backends are
  pluggable (``flexible_reports.query_backends``). The django_tables2 adapter
  now consumes a filtered queryset from each datasource instead of a raw ``Q``
  object. Existing datasources keep working unchanged (default ``dsl``).

.. _DjangoQL: https://github.com/ivelum/djangoql

```

- [ ] **Step 3: Commit**

```bash
git add docs/usage.rst HISTORY.rst
git commit -m "docs: document DjangoQL query language support

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Confirm no migration drift**

Run: `.venv/bin/python manage.py makemigrations --check --dry-run`
Expected: `No changes detected`

- [ ] **Step 2: Run the entire test suite**

Run: `.venv/bin/pytest test_app/tests tests -v`
Expected: all tests PASS (no regressions in templatetags, models, admin, adapters).

- [ ] **Step 3: Lint the changed files**

Run: `.venv/bin/ruff check flexible_reports test_app`
Expected: no errors (the project selects `E`, `F`, `W`).

- [ ] **Step 4 (optional): If anything failed, stop and debug**

Use superpowers:systematic-debugging before changing the plan. Do not paper over a failure with a `try/except` — per project rules, no silent error swallowing.

---

## Self-Review (performed while writing this plan)

**Spec coverage:**
- "Add DjangoQL as a query language alongside django-dsl" → Tasks 2-5.
- "Templates with params, substituted in production, then DjangoQL query" → `DjangoQLQueryBackend._render` (Task 2); covered by `test_djangoql_filter_queryset_uses_template_context`; documented in Task 6.
- "Validate/parse a DjangoQL query at save time, analogous to DSL" → `DjangoQLQueryBackend.validate` via `apply_search(...).first()` (Task 2); wired into `Datasource.clean()` (Task 3) and surfaced in admin (Task 4).
- "Where does the switch live?" → `query_language` on `Datasource` with default `dsl` for free backward compatibility (Task 3 + migration).
- Backward compatibility of stored DSL datasources → migration defaults to `dsl`; `get_filter()` preserved for DSL; existing `test_datasource`/`test_catchall_except_catchall` kept as regression guards (Tasks 3, 5).

**Placeholder scan:** No TBD/TODO/"handle edge cases"/"similar to Task N" — every code and test block is complete and self-contained.

**Type/name consistency:** `query_language`, `dsl_query`, `get_backend()`, `filter_queryset(base_queryset, context=None)`, `get_filter(query, model, context=None)`, `validate(query, model)`, constants `DSL`/`DJANGOQL`/`QUERY_LANGUAGE_CHOICES`, and the ValidationError field key `"dsl_query"` are used identically across the model, backends, admin, adapter, and tests. The migration's `choices`/`verbose_name` match the model field (verified via `makemigrations --check` in Tasks 3 and 7).

## Notes / accepted trade-offs

- **`get_filter()` is DSL-only.** It is kept for backward compatibility (published API + existing tests) and raises `NotImplementedError` for DjangoQL, because DjangoQL has no public API that returns a `Q`. All internal consumption goes through `filter_queryset()`.
- **Templated queries must use `|default:`** so the empty-context render done at validation time still parses — this is exactly today's django-dsl behaviour, now mirrored for DjangoQL.
- **Optional follow-up (not in scope):** DjangoQL ships an admin completion widget (`DjangoQLSearchMixin`) and a custom `DjangoQLSchema` for restricting/relabelling searchable fields. Neither is required for this feature; add later if desired (the widget needs `djangoql` in `INSTALLED_APPS`).
