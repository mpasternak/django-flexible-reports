==============
The data model
==============

Six models make up a report definition. All of them live in
``flexible_reports.models`` and all of them are editable in the Django admin.

.. code-block:: text

    Datasource ──┐                      Table ──┬── Column
    (which rows) │                   (how it is │   (one per rendered column)
                 │                    rendered) │
                 │                              └── ColumnOrder
                 │                                  (default sort order)
                 │                                        │
                 └──────────► ReportElement ◄─────────────┘
                              (one section of a report)
                                     │
                                     ▼
                                  Report
                              (title, slug, layout template)

Read it as: a **Report** has several **ReportElements**; each element takes its
rows from a **Datasource** (or from "everything the other datasources missed")
and renders them with a **Table**, which owns **Columns** and their default
**ColumnOrder**.

A ``Table`` may be shared by any number of elements and reports -- the demo
report renders the same table three times with three different sets of rows.

.. _concept-datasource:

Datasource
==========

*"Which rows go into this section?"*

A datasource does **not** query the database on its own. It takes the base
queryset the view handed to the report (``Report.set_base_queryset()``) and
narrows it. Whatever your view excludes can never show up in a report.

============================ ==================================================
``label``                    Name shown in the admin.
``base_model``               ``ContentType`` of the model being queried. Used to
                             resolve field names and query shortcuts.
``query_language``           ``"dsl"`` (django-dsl, the default) or
                             ``"djangoql"``. See :doc:`queries`.
``dsl_query``                The query itself. Despite the field name it holds
                             a query in whichever language ``query_language``
                             selects.
``sample_context``           JSON object with example values for the query's
                             template parameters, e.g. ``{"min_pages": 300}``.
                             Used **only** to validate the query on save.
``distinct``                 Apply ``.distinct()`` to the resulting queryset
                             (default: on). Queries that join across a
                             to-many relation otherwise duplicate rows.
============================ ==================================================

Methods worth knowing:

``filter_queryset(base_queryset, context=None)``
    Returns ``base_queryset`` narrowed by the query. This is what the renderer
    calls.

``get_filter(context=None)``
    Returns a ``Q`` object. Only the django-dsl backend can do this; the
    DjangoQL backend raises ``NotImplementedError``.

``clean()``
    Runs the backend's ``validate()`` against ``base_model`` using
    ``sample_context``, so saving a broken query fails loudly.

.. _concept-table:

Table
=====

*"How are those rows rendered?"*

============================ ==================================================
``label``                    Name shown in the admin.
``base_model``               ``ContentType`` the columns' ``attr_name`` values
                             are validated against.
``sort_option``              How this table cooperates with other tables on the
                             page -- see below.
``group_prefix``             Only for *sort in group*: the shared prefix.
``attrs``                    JSON dict of HTML attributes for the ``<table>``
                             element, e.g. ``{"class": "report-table"}``.
``empty_template``           Markup shown instead of the table when there are
                             no rows. Rendered as safe HTML.
============================ ==================================================

Sort options
------------

django-tables2 puts the current ordering in a GET parameter. The *prefix* of
that parameter decides which tables on a page move together:

``sort with other tables`` (``SortWithOtherTables``, id ``0``, the default)
    Empty prefix. Every table on the page marked this way and having a column
    with the same *label* re-sorts at once.

``sort individually`` (``SortIndividually``, id ``1``)
    Prefix is the table's primary key, so this table sorts on its own.

``sort in group`` (``SortInGroup``, id ``2``)
    Prefix is ``group_prefix``; all tables sharing that value move together.
    ``group_prefix`` becomes required (enforced in ``clean()``).

.. _concept-column:

Column
======

*"What does one cell look like?"*

A column is either **attribute driven** (``attr_name``), **template driven**
(``template``), or both.

============================ ==================================================
``label``                    Column header. Also the key django-tables2 sorts
                             by, which is what makes "sort with other tables"
                             match columns across tables.
``attr_name``                Attribute on the table's base model. Dot notation
                             crosses relations: ``author.name``. Validated in
                             ``clean()``. **Required if the column is
                             sortable** -- there would be nothing to sort by.
``template``                 Django template snippet for the cell. Defaults to
                             ``{{ value }}``. Gets ``record``, ``value`` and
                             ``default`` in its context, plus everything from
                             the surrounding page context.
``attrs``                    JSON dict of HTML attributes, e.g.
                             ``{"th": {"class": "col-num"},
                             "td": {"class": "col-num"}}``.
``sortable``                 Whether the header is clickable (default: on).
``position``                 Order of the column in the table.
``display_totals``           Render a footer cell for this column.
``footer_template``          Template for that footer cell. Gets ``value`` (the
                             sum of the column, or the row count if the values
                             cannot be added), ``count`` (number of rows) and
                             ``error`` (the exception text, if summing failed).
``exclude_from_export``      Drop this column from non-HTML exports.
``strip_html_on_export``     Strip HTML tags from the value on export
                             (default: on).
============================ ==================================================

``clean()`` refuses a column that has neither ``attr_name`` nor ``template``,
one that is sortable without an ``attr_name``, one whose ``attr_name`` does not
resolve on the base model, and one with ``display_totals`` but no
``footer_template``.

.. _concept-columnorder:

ColumnOrder
===========

The table's **default** ordering -- what the user sees before clicking any
header. Any number of rows per table:

============================ ==================================================
``table``                    The table being ordered.
``column``                   Which column to order by.
``desc``                     Descending instead of ascending.
``position``                 Precedence: ``position=0`` is the primary sort key.
============================ ==================================================

In the admin the *Column* choice is restricted to sortable columns of the table
being edited.

.. _concept-report:

Report
======

*"A page made of several tables."*

============================ ==================================================
``title``                    Shown by the default layout template.
``slug``                     How your view looks the report up.
``template``                 Django template source for the report's layout.
                             Defaults to the contents of
                             ``flexible_reports/templates/flexible_reports/report.html``
                             and is validated on save (it has to compile).
============================ ==================================================

Two setters have to be called before rendering (see :doc:`rendering`):

``set_base_queryset(queryset)``
    Mandatory. Reading ``report.base_queryset`` without it raises
    ``ImproperlyConfigured``.

``set_context(context)``
    Optional. A dict used to render parametrised queries.

Both store their value on the in-memory instance only; nothing is written to
the database.

.. _concept-reportelement:

ReportElement
=============

One section of a report: a title, a source of rows and a table to render them
with.

============================ ==================================================
``parent``                   The report.
``title``                    Section heading.
``slug``                     Key under which the element appears in the layout
                             template's ``elements`` dict. Unique per report.
``position``                 Order within the report.
``data_from``                ``DATA_FROM_DATASOURCE`` (``0``) or
                             ``DATA_FROM_EXCEPT_CATCHALL`` (``2``).
``datasource``               Set for ``DATA_FROM_DATASOURCE``, must be empty
                             otherwise.
``base_model``               Set for ``DATA_FROM_EXCEPT_CATCHALL``, must be
                             empty otherwise.
``table``                    The table used to render the rows.
============================ ==================================================

``clean()`` enforces exactly those combinations.

Except-catchall
---------------

An element with ``data_from = DATA_FROM_EXCEPT_CATCHALL`` shows **everything
from the base queryset that none of the report's datasource-backed elements
picked up**, for the given ``base_model``. It is how you build a report that
ends with an "everything else" table without having to write the complementary
query by hand -- and, more usefully, without having to keep that query in sync
when someone edits the other datasources in the admin.

Behaviour to be aware of:

* The set of "caught" rows is collected per model, keyed by
  ``app_label`` + ``ContentType.model``. Only datasource-backed elements *of
  this report* count as catching anything.
* The exclusion set is built after every datasource element has been processed,
  so the ``position`` of the except-catchall element within the report does not
  matter.
* If no datasource in the report targets the element's ``base_model``, the
  element renders **empty** rather than "everything" -- there is no catchall
  entry for that model to subtract from.

Behaviours (mixins)
===================

The models above are assembled from small abstract bases in
``flexible_reports.models.behaviors``, which is also what
``flexible_reports.models`` re-exports:

``Labelled``
    ``label`` text field; ``__str__`` returns it; default ordering by label.

``Titled``
    ``title`` text field; ``__str__`` returns it.

``Orderable``
    ``position`` integer, default ordering by it. The field is named
    ``position`` because that is what grappelli's sortable inlines expect.

``WithBaseModel``
    ``base_model`` foreign key to ``ContentType``.
