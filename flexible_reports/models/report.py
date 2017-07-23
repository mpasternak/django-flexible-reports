# -*- encoding: utf-8 -*-
import copy
from collections import OrderedDict

from django.db import models
from django.template.base import Template
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Titled
from .validators import TemplateValidator


class ReportElement(Titled, Orderable):
    parent = models.ForeignKey('flexible_reports.Report')
    datasource = models.ForeignKey('flexible_reports.Datasource')
    table = models.ForeignKey('flexible_reports.Table')
    slug = models.CharField(max_length=200)

    class Meta:
        unique_together = [
            ('parent', 'position'),
            ('parent', 'slug')
        ]
        ordering = ('position',)


def _get_template(name):
    t = get_template(name)
    return t.template.source


def get_reports_template():
    return _get_template("flexible_reports/report.html")


class Report(Titled):
    """Report is a collection of multiple Datasources' data
    rendered in Tables. """

    slug = models.SlugField()

    template = models.TextField(
        default=get_reports_template,
        validators=[TemplateValidator, ]
    )

    class Meta:
        verbose_name_plural = _("Reports")
        verbose_name = _("Report")

    def set_base_queryset(self, queryset):
        self.base_queryset = queryset

    def as_html(self, parent_context=None):
        render_context = copy.copy(parent_context)
        render_context.update({
            'self': self,
            'tables': OrderedDict()
        })

        for elem in self.reportelement_set.all().select_related():
            datasource = elem.datasource
            object_list = self.base_queryset.filter(
                datasource.get_filter()
            )

            table_dict = {
                'title': elem.title,
                'subtitle': elem.subtitle,
                'object_list': object_list,
                'as_django_tables2': elem.table.as_django_tables2(object_list)
            }

            render_context['tables'][elem.slug] = table_dict

        return Template(self.template).render(render_context)
