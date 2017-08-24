# -*- encoding: utf-8 -*-
import copy
import itertools
import sys
from collections import OrderedDict

import lxml.html
from django.http.response import HttpResponse
from django.template.base import Template, Context
from django.utils.safestring import mark_safe
from django_tables2.columns.templatecolumn import TemplateColumn, Column
from django_tables2.export.export import TableExport
from django_tables2.tables import Table
from tablib.core import Databook


class CounterMixin:
    def __init__(self):
        self._counter = itertools.count(1)

    def counter(self):
        return str(self._counter.__next__())


def render_footer(bound_column, table):
    try:
        value = sum([getattr(x, bound_column.column.accessor)
                     for x in table.data])
    except Exception as e:
        value = str(e)

    context = Context({'value': value})

    return Template(
        bound_column.column.footer_template
    ).render(context=context)


class FooterMixin:
    def __init__(self, display_totals, footer_template, kwargs):
        self.display_totals = display_totals
        self.footer_template = footer_template

        if display_totals:
            kwargs['footer'] = render_footer


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


def table(table, request, object_list):
    extra_columns = []
    for c in table.column_set.all():
        extra_columns.append(column(c))

    class AdHocTable(Table):
        class Meta:
            per_page = sys.maxsize

    return AdHocTable(
        data=object_list,
        prefix=table.get_prefix(),
        extra_columns=extra_columns,
        request=request,
        attrs=table.attrs,
        empty_text=mark_safe(table.empty_template))


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
                object_list)
        }

        render_context['elements'][elem.slug] = table_dict

    return render_context


def as_html(report, parent_context):
    render_context = _report(report, parent_context)
    return Template(report.template).render(render_context)


def as_xlsx_databook(report, parent_context):
    render_context = _report(report, parent_context)

    databook = Databook()
    for element in render_context['elements'].values():
        dataset = TableExport(
            TableExport.XLSX,
            element['table']
        ).dataset

        dataset.title = element['title']
        databook.add_sheet(dataset)

    return databook


def as_docx_response(report, parent_context, filename=None):
    data = as_html(report, parent_context)

    response = HttpResponse(
        """<head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" /> 
        </head><body>""" + data + "</body>",
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

    if filename is None:
        filename = report.title + ".docx"

    response['Content-Disposition'] = 'attachment; filename="{}"'.format(
        filename
    )
    response['Content-Length'] = len(data)
    return response


def as_xlsx_response(report, parent_context, filename=None):
    response = HttpResponse(content_type=TableExport.FORMATS[TableExport.XLSX])
    if filename is None:
        filename = report.title + ".xlsx"

    response['Content-Disposition'] = 'attachment; filename="{}"'.format(
        filename
    )

    xlsx = as_xlsx_databook(report, parent_context)
    data = xlsx.export(TableExport.XLSX)
    response['Content-Length'] = len(data)
    response.write(data)
    return response
