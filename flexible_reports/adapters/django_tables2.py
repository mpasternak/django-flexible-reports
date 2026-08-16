import copy
import operator
import sys
from collections import OrderedDict, defaultdict
from functools import lru_cache, reduce
from tempfile import NamedTemporaryFile

import bleach
import lxml.html
import pypandoc
from django.template import Context
from django.template.base import Template
from django.utils.safestring import mark_safe
from django_tables2.columns.templatecolumn import Column, TemplateColumn
from django_tables2.export.export import TableExport
from django_tables2.tables import Table
from tablib.core import Databook, Dataset

from flexible_reports.models.report import DATA_FROM_DATASOURCE


@lru_cache(maxsize=512)
def _compiled_template(template_code):
    """Compile a template once per distinct template source.

    ``TemplateColumn.render`` compiles its template for every single cell,
    which dominates the cost of rendering a large table. The cache is keyed by
    the template source, so it needs no invalidation: editing a template in the
    database produces a different string, hence a different key.

    The compiled ``Template`` must never be pinned onto a column instance:
    columns live in ``Table.base_columns`` and are deep-copied on every table
    instantiation, and a ``Template`` holds a reference to the template engine.

    ``cache_clear()`` is available for tests that swap the template engine with
    ``override_settings(TEMPLATES=...)``, as a cached ``Template`` remembers the
    engine active at compilation time.
    """
    return Template(template_code)


class CounterMixin:
    def __init__(self):
        # Kolumny są trzymane w ``Table.base_columns`` i kopiowane przez
        # ``copy.deepcopy`` przy każdej instancjacji tabeli. Od Pythona
        # 3.14 ``itertools.count`` traci wsparcie dla ``copy``/``deepcopy``
        # (DeprecationWarning w 3.13, błąd w 3.14), więc licznik trzymamy
        # jako zwykły ``int``.
        self._counter = 0

    def counter(self):
        self._counter += 1
        return str(self._counter)


class FooterMixin:
    def __init__(self, display_totals, footer_template, kwargs):
        self.display_totals = display_totals
        self.footer_template = footer_template

        if self.display_totals:
            self.render_footer = self._render_footer

    def _render_footer(self, table):
        error = None
        try:
            value = sum([getattr(x, self.accessor) for x in table.data])
        except Exception as e:
            error = str(e)
            value = len(table.data)

        context = Context({"value": value, "error": error, "count": len(table.data)})

        return _compiled_template(self.footer_template).render(context=context)


class StripHTMLOnExportMixin:
    def __init__(self, strip_html_on_export):
        self.strip_html_on_export = strip_html_on_export

    def value(self, **kwargs):
        value = super().value(**kwargs)
        if self.strip_html_on_export is True:
            value = lxml.html.fromstring(str(value)).text_content()
        return value


class DjangoTables2TemplateColumn(
    StripHTMLOnExportMixin, CounterMixin, FooterMixin, TemplateColumn
):
    def __init__(
        self, display_totals, footer_template, strip_html_on_export, *args, **kw
    ):
        FooterMixin.__init__(self, display_totals, footer_template, kw)
        StripHTMLOnExportMixin.__init__(self, strip_html_on_export)
        CounterMixin.__init__(self)
        TemplateColumn.__init__(self, *args, **kw)

    def render(self, record, table, value, bound_column, **kwargs):
        # This is the body of ``TemplateColumn.render``, with the per-cell
        # ``Template(self.template_code)`` compilation replaced by the
        # module-level, content-keyed cache.
        #
        # Columns rendering a template file (``template_name``) go through the
        # parent, and so do old django-tables2 releases without
        # ``get_context_data`` -- ``pyproject.toml`` only requires
        # ``django-tables2>=1.16.0``, which predates that method.
        if not self.template_code or not hasattr(self, "get_context_data"):
            return super().render(
                record=record,
                table=table,
                value=value,
                bound_column=bound_column,
                **kwargs,
            )

        # If the table is being rendered using `render_table`, it hackily
        # attaches the context to the table as a gift to `TemplateColumn`.
        parent_context = getattr(table, "context", Context())

        context = self.get_context_data(
            record=record, table=table, value=value, bound_column=bound_column, **kwargs
        )
        # ``update`` is used as a context manager on purpose: the cell
        # variables have to be popped again once the cell has been rendered,
        # otherwise they leak into the next cell.
        with parent_context.update(context):
            request = getattr(table, "request", None)
            parent_context["request"] = request
            return _compiled_template(self.template_code).render(parent_context)


class DjangoTables2Column(StripHTMLOnExportMixin, FooterMixin, Column):
    def __init__(
        self, display_totals, footer_template, strip_html_on_export, *args, **kw
    ):
        FooterMixin.__init__(self, display_totals, footer_template, kw)
        StripHTMLOnExportMixin.__init__(self, strip_html_on_export)
        Column.__init__(self, *args, **kw)


def column(column):
    kwargs = dict(
        verbose_name=column.label,
        orderable=column.sortable,
        order_by=column.attr_name,
        display_totals=column.display_totals,
        footer_template=column.footer_template,
        accessor=column.attr_name,
        exclude_from_export=column.exclude_from_export,
        strip_html_on_export=column.strip_html_on_export,
        attrs=column.attrs,
    )

    if column.template:
        klass = DjangoTables2TemplateColumn(template_code=column.template, **kwargs)

    else:
        klass = DjangoTables2Column(**kwargs)

    return (column.label, klass)


def _table(table, ordering_overridden=False):
    # The class is rebuilt on every call. It used to be cached per ``Table.pk``
    # for the lifetime of the process, which made label changes and removed
    # columns invisible until a restart. The cache saved ~0.5 ms per render,
    # far less than caching the compiled column templates does.
    #
    # ``ordering_overridden`` means the caller already ordered the queryset via
    # ``Report.set_order_by``. The table's own ``ColumnOrder`` must then be
    # dropped rather than merely ignored: django-tables2 applies
    # ``Meta.order_by`` to the data unconditionally, so leaving it in place
    # would re-sort the rows and undo the override. With an empty ordering it
    # skips the queryset entirely (``if accessors:`` in its ``data.py``) and
    # the caller's ``order_by`` survives.
    order_by = []
    if not ordering_overridden:
        for column_order in (
            table.columnorder_set.all().select_related().order_by("position")
        ):
            order_by.append(column_order.get())
    table.order_by = order_by

    class AdHocTable(Table):
        class Meta:
            attrs = table.attrs or {}
            order_by = table.order_by
            per_page = sys.maxsize
            prefix = table.get_prefix()
            empty_text = mark_safe(table.empty_template)

    for c in table.column_set.all():
        label, klass = column(c)
        AdHocTable.base_columns[label] = klass

    return AdHocTable


def table(table, request, object_list, ordering_overridden=False):
    return _table(table, ordering_overridden)(data=object_list, request=request)


def _report(report, parent_context):
    render_context = copy.copy(parent_context)

    # elements -> an OrderedDict of
    #   table,
    #   title,
    #   object_list
    # keys are slugs of elements.
    #
    # catchall -> a dict, one entry per datasource.model,
    #   every item is a filtered queryset produced by datasource.filter_queryset;
    #   it is used to track all the items in the report, per model
    #
    # except_catchall -> a dict, one per datasource.model, contains
    #   QuerySets with all the items, that were not caught by catchall
    #
    # this may be used to render a few datasources in tables, then to
    # have a table containing everything except those records
    #

    render_context.update(
        {
            "self": report,
            "elements": OrderedDict(),
            "catchall": defaultdict(lambda: []),
            "except_catchall": defaultdict(lambda: []),
        }
    )

    order_by = report.order_by

    reportelements_set = (
        report.reportelement_set.all()
        .prefetch_related("datasource", "datasource__base_model", "table")
        .select_related()
    )
    for elem in reportelements_set:
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

            # Ordering is applied here, after the queryset has been handed to
            # ``catchall``: those copies get OR-ed together further down, and an
            # ORDER BY on the operands only muddies that combination.
            if order_by:
                object_list = object_list.order_by(*order_by)

            table_dict = {
                "title": elem.title,
                "object_list": object_list,
                "table": table(
                    elem.table,
                    parent_context["request"],
                    object_list,
                    ordering_overridden=bool(order_by),
                ),
            }

        else:
            table_dict = {
                "except_catchall": elem.base_model,
                "title": elem.title,
                "table": elem.table,
            }

        render_context["elements"][elem.slug] = table_dict

    # Fill except-catchall.
    # ``catchall`` holds the already-filtered querysets produced by each
    # datasource (instead of raw Q objects). All querysets under one key filter
    # the same ``report.base_queryset``, so we OR them into a single queryset
    # and exclude its primary keys in one go -- equivalent to the previous
    # OR-of-Q behaviour, but with one subquery per model instead of one per
    # datasource.
    except_catchall = report.base_queryset.all()
    for key, querysets in render_context["catchall"].items():
        if not querysets:
            continue

        caught = reduce(operator.or_, querysets)
        except_catchall = except_catchall.exclude(
            pk__in=caught.values_list("pk", flat=True)
        )

        render_context["except_catchall"][key] = except_catchall

    for key, elem in render_context["elements"].items():
        if "except_catchall" not in elem:
            continue

        base_model = elem["except_catchall"]

        # Match the key built when filling ``except_catchall`` above, which uses
        # ContentType.model. ContentType.name (the verbose name) differs from
        # the model name for most models, so using it here misses the lookup
        # and renders an empty table.
        key = "%s_%s" % (base_model.app_label, base_model.model)

        object_list = render_context["except_catchall"][key]
        if order_by:
            object_list = object_list.order_by(*order_by)
        elem["object_list"] = object_list
        elem["table"] = table(
            elem["table"],
            parent_context["request"],
            object_list,
            ordering_overridden=bool(order_by),
        )

    return render_context


def as_html(report, parent_context):
    render_context = _report(report, parent_context)
    return Template(report.template).render(render_context)


def as_docx(
    report,
    parent_context,
    allowed_tags=[
        "table",
        "tr",
        "td",
        "th",
        "b",
        "i",
        "u",
        "sup",
        "sub",
        "h1",
        "h2",
        "h3",
        "h4",
        "em",
        "strong",
        "strike",
        "font",
    ],
    allowed_attributes={"td": ["colspan"]},
):
    data = as_html(report, parent_context)
    # Remove "<a>" tags from headers
    data = bleach.clean(data, allowed_tags, allowed_attributes, strip=True)
    f = NamedTemporaryFile(delete=False)
    pypandoc.convert_text(data, "docx", format="html", outputfile=f.name)
    return f


def as_tablib_databook(report, parent_context):
    render_context = _report(report, parent_context)

    databook = Databook()
    for element in render_context["elements"].values():
        dataset = TableExport(TableExport.XLSX, element["table"]).dataset

        dataset.title = element["title"][:31]
        databook.add_sheet(dataset)

    return databook


def as_tablib_dataset(report, parent_context):
    render_context = _report(report, parent_context)

    dataset = Dataset()
    for element in render_context["elements"].values():
        table = element["table"]
        dataset.append_separator(element["title"])
        for i, row in enumerate(table.as_values()):
            dataset.append(row)

    return dataset
