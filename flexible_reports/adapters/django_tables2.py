# -*- encoding: utf-8 -*-
import copy
import itertools
from collections import OrderedDict

from django.template.base import Template, Context
from django.utils.safestring import mark_safe
from django_tables2.columns.templatecolumn import TemplateColumn, Column
from django_tables2.tables import Table


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


class DjangoTables2TemplateColumn(CounterMixin, FooterMixin, TemplateColumn):
    def __init__(self, display_totals, footer_template, *args, **kw):
        FooterMixin.__init__(self, display_totals, footer_template, kw)
        TemplateColumn.__init__(self, *args, **kw)
        CounterMixin.__init__(self)


class DjangoTables2Column(FooterMixin, Column):
    def __init__(self, display_totals, footer_template, *args, **kw):
        FooterMixin.__init__(self, display_totals, footer_template, kw)
        Column.__init__(self, *args, **kw)


def column(column):
    kwargs = dict(
        verbose_name=column.label,
        orderable=column.sortable,
        order_by=column.attr_name,
        display_totals=column.display_totals,
        footer_template=column.footer_template,
        accessor=column.attr_name
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

    return Table(
        data=object_list,
        prefix=table.get_prefix(),
        extra_columns=extra_columns,
        request=request,
        empty_text=mark_safe(table.empty_template))


def report(report, parent_context):
    render_context = copy.copy(parent_context)
    render_context.update({
        'self': report,
        'elements': OrderedDict()
    })

    for elem in report.reportelement_set.all().select_related():
        datasource = elem.datasource
        object_list = report.base_queryset.filter(
            datasource.get_filter()
        )

        if datasource.distinct:
            object_list = object_list.distinct()

        table_dict = {
            'title': elem.title,
            'subtitle': elem.subtitle,
            'object_list': object_list,
            'table': table(
                elem.table,
                parent_context['request'],
                object_list)
        }

        render_context['elements'][elem.slug] = table_dict

    return Template(report.template).render(render_context)
