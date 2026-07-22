# Query languages

A `Datasource` narrows the report's base queryset with a textual query. Which
language that query is written in is chosen per datasource, in the
`query_language` field.

Both languages are exposed through the same small backend interface in
`flexible_reports.query_backends`:

```python
from flexible_reports.query_backends import DSL, DJANGOQL, get_backend

backend = get_backend(DSL)
backend.filter_queryset(base_queryset, query, context=None)  # -> QuerySet
backend.validate(query, model, context=None)                 # -> None / raises
backend.get_filter(query, model, context=None)               # -> Q (dsl only)
```

## `django-dsl` (`"dsl"`, the default)

[django-dsl][django-dsl] compiles a compact boolean expression into a Django
`Q` object:

```text
i > 0 AND i < 10
author = "Ursula K. Le Guin"
```

Because it produces a `Q`, `Datasource.get_filter()` works with this
backend, and the filter can be combined with other `Q` objects if you need
to.

This is the default, so datasources created before the query-language field
existed keep working unchanged.

[django-dsl]: https://pypi.org/project/django-dsl/

## `DjangoQL` (`"djangoql"`)

[DjangoQL][djangoql] is a richer, more forgiving language with an
autocompleting editor and introspection of related models:

```text
pages > 300 and author.country = "Poland"
```

The dependency is the [djangoql-iplweb][djangoql-iplweb] fork, which keeps the
`djangoql` import name and adds i18n for parser and schema error messages.

DjangoQL applies its search directly to a queryset, so it cannot produce a
`Q`: `Datasource.get_filter()` raises `NotImplementedError` for this
backend. Use `Datasource.filter_queryset()` (which is what the renderer
calls anyway).

[djangoql]: https://github.com/ivelum/djangoql
[djangoql-iplweb]: https://pypi.org/project/djangoql-iplweb/

## Query shortcuts (django-dsl only)

A model may declare shorthand names for lookups by setting a
`django_dsl_shortcuts` attribute (the name comes from
`flexible_reports.constants.SHORTCUTS_ATTR_NAME`):

```python
class Book(models.Model):
    django_dsl_shortcuts = {
        "author": "author__name",
        "country": "author__country",
    }
```

A datasource over `Book` may then write `author = "Stanisław Lem"` instead
of `author__name = "Stanisław Lem"`. The library picks the attribute up
automatically; nothing has to be registered.

The shortcuts are handed to the django-dsl compiler, so they apply to that
backend only. DjangoQL has its own schema-based introspection and uses real
field names.

## Parametrised queries

**Every query is rendered as a Django template before it is executed**, with
the report's context as the template context. That is how a single stored
report can answer "books longer than N pages" for a runtime-supplied `N`:

```text
pages > {{ min_pages }}
```

```python
report.set_context({"min_pages": 300})
```

The context reaches the datasource through the report; see
[Rendering reports](rendering.md).

Parameter values are **not** HTML-escaped. They feed a query language, not a
web page, and escaping would turn query-significant characters (`<`, `&`,
`"`) into entities and corrupt the query.

!!! warning

    Because the query is a template, whatever you put into the report context
    becomes part of the query text. Do not pass unvalidated user input straight
    into `set_context()`: a value like `0 or True` changes what the query
    selects. Treat the context the way you would treat string interpolation
    into SQL -- validate or coerce (`int(request.GET["n"])`) first.

### Validating a parametrised query

Saving a datasource validates its query: the backend compiles it and runs a
trial `.first()` against the database, raising `ValidationError` if either
step fails. A parametrised query with an empty context would render to
`pages >` and fail to compile, so the `sample_context` field supplies
example values used *only* for that validation:

```python
Datasource(
    label="Long books",
    base_model=book_ct,
    query_language=DJANGOQL,
    dsl_query="pages > {{ min_pages }}",
    sample_context={"min_pages": 300},
)
```

`sample_context` must be a JSON object (a dict) or empty; anything else is a
validation error. Alternatively, give the parameter a template default --
`pages > {{ min_pages|default:0 }}` -- so the query stays valid with no
context at all.

## Errors you can expect

All of these arrive as `django.core.exceptions.ValidationError` on the
`dsl_query` field, so the admin shows them next to the query box:

* an empty query;
* a query that does not compile (`CompileException` for django-dsl,
  `DjangoQLError` for DjangoQL -- typically an unknown field);
* a query that compiles but that the database rejects.

The original exception is chained (`raise ... from e`), so the traceback
still shows the underlying error.
