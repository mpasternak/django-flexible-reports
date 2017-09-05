# -*- encoding: utf-8 -*-
import copy
import itertools
import sys
from collections import OrderedDict
from tempfile import NamedTemporaryFile

import bleach
import lxml.html
import pypandoc
from django.template.base import Template, Context
from django.utils.safestring import mark_safe
from django_tables2.columns.templatecolumn import TemplateColumn, Column
from django_tables2.export.export import TableExport
from django_tables2.tables import Table
from tablib.core import Databook, Dataset


class CounterMixin:
    def __init__(self):
        self._counter = itertools.count(1)

    def counter(self):
        return str(self._counter.__next__())


class FooterMixin:
    def __init__(self, display_totals, footer_template, kwargs):
        self.display_totals = display_totals
        self.footer_template = footer_template

        if self.display_totals:
            self.render_footer = self._render_footer

    def _render_footer(self, table):
        try:
            value = sum([getattr(x, self.accessor)
                         for x in table.data])
        except Exception as e:
            value = str(e)

        context = Context({'value': value})

        return Template(
            self.footer_template
        ).render(context=context)


class StripHTMLOnExportMixin:
    def __init__(self, strip_html_on_export):
        self.strip_html_on_export = strip_html_on_export

    def value(self, **kwargs):
        value = super(StripHTMLOnExportMixin, self).value(**kwargs)
        if self.strip_html_on_export is True:
            value = lxml.html.fromstring(str(value)).text_content()
        return value


class DjangoTables2TemplateColumn(StripHTMLOnExportMixin, CounterMixin,
                                  FooterMixin, TemplateColumn):
    def __init__(self, display_totals, footer_template, strip_html_on_export,
                 *args, **kw):
        FooterMixin.__init__(self, display_totals, footer_template, kw)
        StripHTMLOnExportMixin.__init__(self, strip_html_on_export)
        CounterMixin.__init__(self)
        TemplateColumn.__init__(self, *args, **kw)


class DjangoTables2Column(StripHTMLOnExportMixin, FooterMixin, Column):
    def __init__(self, display_totals, footer_template, strip_html_on_export,
                 *args, **kw):
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
        attrs=column.attrs
    )

    if column.template:
        klass = DjangoTables2TemplateColumn(
            template_code=column.template,
            **kwargs)

    else:
        klass = DjangoTables2Column(**kwargs)

    return (column.label, klass)


_table_cache = {}


def _table(table):
    global _table_cache

    if table.pk not in _table_cache:
        order_by = []
        for column_order in table.columnorder_set.all() \
            .select_related().order_by("position"):
            order_by.append(column_order.get())
        table.order_by = order_by

        class AdHocTable(Table):
            class Meta:
                attrs = table.attrs or {}
                order_by = table.order_by
                per_page = sys.maxsize
                prefix = table.get_prefix()
                empty_text = mark_safe(table.empty_template)

        extra_columns = []
        for c in table.column_set.all():
            label, klass = column(c)
            AdHocTable.base_columns[label] = klass
            # extra_columns.append(column(c))

        _table_cache[table.pk] = AdHocTable

    return _table_cache[table.pk]

def table(table, request, object_list):
    return _table(table)(data=object_list, request=request)

def _report(report, parent_context):
    render_context = copy.copy(parent_context)
    render_context.update({
        'self': report,
        'elements': OrderedDict()
    })

    for elem in report.reportelement_set.all().select_related():
        datasource = elem.datasource
        object_list = report.base_queryset.filter(
            datasource.get_filter(context=report.context)
        )

        if datasource.distinct:
            object_list = object_list.distinct()

        table_dict = {
            'title': elem.title,
            'object_list': object_list,
            'table': table(
                elem.table,
                parent_context['request'],
                object_list.select_related())
        }

        render_context['elements'][elem.slug] = table_dict

    return render_context


def as_html(report, parent_context):
    render_context = _report(report, parent_context)
    return Template(report.template).render(render_context)


def as_docx(report,
            parent_context,
            allowed_tags=['table', 'tr', 'td', 'th', 'b', 'i', 'u',
                          'sup', 'sub', 'h1', 'h2', 'h3', 'h4',
                          'em', 'strong', 'strike', 'font'],
            allowed_attributes={"td": ["colspan"]}):
    data = as_html(report, parent_context)
    # Remove "<a>" tags from headers
    data = bleach.clean(data, allowed_tags, allowed_attributes, strip=True)
    f = NamedTemporaryFile(delete=False)
    pypandoc.convert_text(data, 'docx', format='html', outputfile=f.name)
    return f


def as_tablib_databook(report, parent_context):
    render_context = _report(report, parent_context)

    databook = Databook()
    for element in render_context['elements'].values():
        dataset = TableExport(
            TableExport.XLSX,
            element['table']
        ).dataset

        dataset.title = element['title'][:31]
        databook.add_sheet(dataset)

    return databook

def as_tablib_dataset(report, parent_context):
    render_context = _report(report, parent_context)

    dataset = Dataset()
    for element in render_context['elements'].values():
        table = element['table']
        dataset.append_separator(element['title'])
        for i, row in enumerate(table.as_values()):
            dataset.append(row)

    return dataset
