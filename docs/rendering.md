# Rendering reports

## From a view

Three steps, always the same:

```python
from django.shortcuts import render

from flexible_reports.models import Report

from .models import Book


def library_report(request):
    report = Report.objects.get(slug="library-report")
    report.set_base_queryset(Book.objects.select_related("author"))
    report.set_context({"min_pages": 300})
    return render(request, "library/report.html", {"report": report})
```

`set_base_queryset(queryset)`
:   **Mandatory.** Every datasource in the report narrows *this* queryset;
    nothing outside it can appear in the report. Reading
    `report.base_queryset` without having set it raises
    `django.core.exceptions.ImproperlyConfigured`.

    This is also the right place for `select_related()` /
    `prefetch_related()`: columns reaching across relations
    (`attr_name="author.name"`) will otherwise issue a query per row.

`set_context(context)`
:   Optional. A dict used to render parametrised queries -- see
    [Query languages](queries.md). Defaults to `None`, which the backends
    treat as an empty context.

Both setters only touch the in-memory instance; nothing is saved.

## The template tags

`flexible_reports_tags` provides two tags:

```django
{% load flexible_reports_tags %}

{% flexible report %}
```

`{% flexible report %}`
:   Renders the whole report -- every element, its table, its columns, its sort
    order -- and returns safe HTML. It is a `simple_tag` taking the
    surrounding template context, which it passes on to the renderer.

`{% render some_string %}`
:   Compiles `some_string` as a Django template and renders it with the
    current context. Handy inside a report layout template that keeps snippets
    of markup in the database.

!!! important

    `django.template.context_processors.request` must be enabled. The tag
    hands the parent context to the django-tables2 adapter, which reads
    `request` from it in order to build the table (sorting comes from the
    query string).

## Layout template

`Report.template` holds the Django template source for the report's layout.
Its default is the contents of
`flexible_reports/templates/flexible_reports/report.html`:

```django
{% load render_table from django_tables2 %}

<h1>{{ self.title }}</h1>

{% for element in elements.values %}
    <h3>{{ element.title }}</h3>

    {% render_table element.table %}
{% empty %}
    No tables defined for this report. Please add some tables in the
    admin interface.
{% endfor %}
```

Edit it in the admin (*Reports → Template*) to change the layout. It is
validated on save: a template that does not compile is rejected.

The layout template is rendered with the **page context plus**:

| Variable | Meaning |
|----------|---------|
| `self` | The `Report` instance. |
| `elements` | `OrderedDict` keyed by `ReportElement.slug`, in `position` order. Each value is a dict with `title`, `object_list` and `table` (a ready django-tables2 table instance). |
| `catchall` | Per model (`applabel_modelname`), the list of filtered querysets the datasource-backed elements produced. |
| `except_catchall` | Per model, the queryset of everything those datasources did *not* catch. |

Because elements are keyed by slug you can lay a report out by hand instead of
looping:

```django
{% load render_table from django_tables2 %}

<h1>{{ self.title }}</h1>

<section class="highlight">
  <h2>{{ elements.long_books.title }}</h2>
  {% render_table elements.long_books.table %}
</section>

<section>
  <h2>The rest</h2>
  {% render_table elements.everything_else.table %}
</section>
```

!!! warning

    Django's template language does not allow `-` in a variable lookup, so
    `{{ elements.long-books.title }}` is a `TemplateSyntaxError`. If you
    intend to address elements by slug from the layout template, give them
    **underscored** slugs (`long_books`); `SlugField` accepts both. The
    looping form above works with any slug.

## Cell templates

A column's `template` is a Django template snippet rendered once per cell,
with the surrounding page context plus:

| Variable | Meaning |
|----------|---------|
| `value` | The value resolved through `attr_name`. |
| `record` | The model instance for the current row. |
| `default` | The column's fallback value. |
| `column` | The bound django-tables2 column. |
| `row_counter` | 0-based index of the row being rendered. |
| `request` | The current request. |

```django
{# a column with attr_name="title" #}
<strong>{{ value }}</strong><br>
<small>{{ record.pages }} pages</small>

{# a column with no attr_name at all -- pure presentation #}
{{ row_counter|add:1 }}
```

Cell templates are compiled once per distinct template *source* and cached for
the process (`flexible_reports.adapters.django_tables2._compiled_template`).
The cache is keyed by the source text, so editing a template in the admin
produces a different key and takes effect immediately -- no restart, no
invalidation.

!!! note

    The table *class* is rebuilt on every render, deliberately. It used to be
    cached per `Table.pk` for the lifetime of the process, which meant a
    renamed or deleted column stayed visible until Django was restarted -- and,
    with several workers, the page flip-flopped between old and new headers
    depending on which worker answered. That cache was removed in 0.4.0.

## Footers

A column with `display_totals` renders `footer_template` with:

| Variable | Meaning |
|----------|---------|
| `value` | `sum()` of the column's values across all rows. If the values cannot be added (text, or no `attr_name` at all) it falls back to the number of rows. |
| `count` | Number of rows. |
| `error` | `str()` of the exception raised while summing, or `None`. |

```django
{# numeric column #}
{{ value|floatformat:2 }} PLN

{# column with no attr_name: value == count #}
{{ count }} book(s)
```

## Empty tables

When an element's queryset is empty, django-tables2 renders the table's
`empty_template` instead of rows. It is marked safe, so it may contain
markup.

## Performance notes

* Put `select_related()` / `prefetch_related()` on the base queryset.
* `per_page` is set to `sys.maxsize`: reports are rendered whole, never
  paginated. A report over a very large queryset will render a very large
  page.
* `Datasource.distinct` (on by default) adds a `DISTINCT` to each element's
  queryset. Turn it off for datasources that do not join across to-many
  relations if it costs you.
