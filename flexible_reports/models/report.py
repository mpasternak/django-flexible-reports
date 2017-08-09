# -*- encoding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Titled
from .validators import TemplateValidator


class ReportElement(Titled, Orderable):
    parent = models.ForeignKey('flexible_reports.Report')
    datasource = models.ForeignKey('flexible_reports.Datasource')
    table = models.ForeignKey('flexible_reports.Table')
    slug = models.SlugField(max_length=200)

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
        verbose_name=_("Template"),
        default=get_reports_template,
        validators=[TemplateValidator, ]
    )

    _base_queryset = None
    @property
    def base_queryset(self):
        if self._base_queryset is None:
            raise ImproperlyConfigured("Please set base queryset for this "
                                       "report using Report.set_base_queryset")
        return self._base_queryset

    class Meta:
        verbose_name_plural = _("Reports")
        verbose_name = _("Report")

    def set_base_queryset(self, queryset):
        self._base_queryset = queryset
