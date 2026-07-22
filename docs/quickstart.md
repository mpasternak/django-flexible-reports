# Quickstart

This chapter builds one working report end to end. It uses the same models the
bundled demo project uses, so everything here can be checked by running
`make demo` (see [The demo project](demo.md)).

## The domain

Two ordinary models -- nothing in them is specific to this library, apart from
one optional convenience:

```python
# demoapp/models.py
from django.db import models


class Author(models.Model):
    name = models.CharField("Name", max_length=200, unique=True)
    country = models.CharField("Country", max_length=100, blank=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    #: Optional. Shorthands usable in django-dsl queries, so a datasource
    #: can say ``author = "Stanisław Lem"`` instead of
    #: ``author__name = "Stanisław Lem"``.
    django_dsl_shortcuts = {
        "author": "author__name",
        "country": "author__country",
    }

    title = models.CharField("Title", max_length=300)
    author = models.ForeignKey(Author, related_name="books",
                               on_delete=models.CASCADE)
    year = models.PositiveIntegerField("Year of publication")
    pages = models.PositiveIntegerField("Pages")
    price = models.DecimalField("Price", max_digits=7, decimal_places=2)
```

## Step 1 -- a datasource

A [Datasource](concepts.md#datasource) says *which rows* end up in a table.
It does not query the database on its own: it narrows a base queryset the view
supplies later.

In the admin: *Flexible reports → Datasources → Add*. In code:

```python
from django.contrib.contenttypes.models import ContentType

from flexible_reports.models import Datasource
from flexible_reports.query_backends import DJANGOQL

book_ct = ContentType.objects.get_for_model(Book)

long_books = Datasource(
    label="Long books",
    base_model=book_ct,
    query_language=DJANGOQL,
    dsl_query="pages > {{ min_pages }}",
    # Example values, used only to validate the query when it is saved.
    sample_context={"min_pages": 300},
)
long_books.full_clean()   # validates the query -- see below
long_books.save()
```

`full_clean()` (which the admin runs for you) compiles the query and executes
a trial `.first()` against the database, so a broken query is rejected at
save time instead of producing a silently empty report. See
[Query languages](queries.md).

## Step 2 -- a table

A [Table](concepts.md#table) says *how* rows are rendered. It is a bag of
[Columns](concepts.md#column):

```python
from flexible_reports.models import Column, ColumnOrder, Table
from flexible_reports.models.table import SortWithOtherTables

table = Table.objects.create(
    label="Books",
    base_model=book_ct,
    sort_option=SortWithOtherTables.id,
    attrs={"class": "report-table"},
    empty_template="No books match this query.",
)

title = Column.objects.create(
    parent=table,
    position=0,
    label="Title",
    attr_name="title",
    template="<strong>{{ value }}</strong><br>"
             "<small>{{ record.pages }} pages</small>",
    sortable=True,
)
# Dot notation crosses the foreign key.
Column.objects.create(
    parent=table, position=1, label="Author",
    attr_name="author.name", template="{{ value }}", sortable=True,
)
year = Column.objects.create(
    parent=table, position=2, label="Year",
    attr_name="year", template="{{ value }}", sortable=True,
)
# A numeric column with a total in the footer.
Column.objects.create(
    parent=table, position=3, label="Price",
    attr_name="price", template="{{ value|floatformat:2 }} PLN",
    sortable=True,
    display_totals=True,
    footer_template="{{ value|floatformat:2 }} PLN",
)

# Default ordering: newest first, then alphabetically by title.
ColumnOrder.objects.create(table=table, column=year, desc=True, position=0)
ColumnOrder.objects.create(table=table, column=title, desc=False, position=1)
```

## Step 3 -- a report

A [Report](concepts.md#report) glues datasources and tables together through
[ReportElements](concepts.md#reportelement):

```python
from flexible_reports.models import Report, ReportElement
from flexible_reports.models.report import (
    DATA_FROM_DATASOURCE,
    DATA_FROM_EXCEPT_CATCHALL,
)

report = Report.objects.create(title="Library report", slug="library-report")

ReportElement.objects.create(
    parent=report, position=0,
    title="Long books", slug="long-books",
    data_from=DATA_FROM_DATASOURCE,
    datasource=long_books,
    table=table,
)
# Everything the datasources above did *not* catch.
ReportElement.objects.create(
    parent=report, position=1,
    title="Everything else", slug="everything-else",
    data_from=DATA_FROM_EXCEPT_CATCHALL,
    datasource=None,
    base_model=book_ct,
    table=table,
)
```

`Report.template` was not given, so it defaults to the source of
`flexible_reports/templates/flexible_reports/report.html`, which renders
every element in order. Edit that field in the admin to change the layout.

## Step 4 -- render it

```python
# views.py
from django.shortcuts import render

from flexible_reports.models import Report

from .models import Book


def library_report(request):
    report = Report.objects.get(slug="library-report")
    # Required: every datasource narrows *this* queryset.
    report.set_base_queryset(Book.objects.select_related("author"))
    # Optional: values for parametrised queries ("pages > {{ min_pages }}").
    report.set_context({"min_pages": 300})
    return render(request, "library/report.html", {"report": report})
```

```django
{# library/report.html #}
{% load flexible_reports_tags %}

<h1>Library</h1>
{% flexible report %}
```

That is the whole integration. Everything else -- which tables the report has,
which columns they carry, how they are sorted, how the cells look -- is read
from the database and editable in the admin.

!!! warning

    `set_base_queryset()` is mandatory. Rendering a report without it raises
    `ImproperlyConfigured`. Nothing outside that queryset can ever appear in
    the report, which is what makes it safe to expose report editing to
    non-developers: they choose among the rows you already decided to show.

## Next steps

* [The data model](concepts.md) -- every field of every model.
* [Query languages](queries.md) -- django-dsl vs DjangoQL, parameters, shortcuts.
* [Rendering reports](rendering.md) -- what the template tag does and what a column template gets.
* [Exporting](exporting.md) -- `.docx`, XLSX, CSV.
* [Cloning](cloning.md) -- copy a table or a report.
