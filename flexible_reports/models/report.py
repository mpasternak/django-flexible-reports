# -*- encoding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Titled
from .validators import TemplateValidator

DATA_FROM_DATASOURCE = 0
DATA_FROM_CATCHALL = 1
DATA_FROM_EXCEPT_CATCHALL = 2

class ReportElement(Titled, Orderable):
    parent = models.ForeignKey('flexible_reports.Report',
                               verbose_name=_("Parent"))
    data_from = models.IntegerField(
        verbose_name=_("Data from"),
        choices=[
            (DATA_FROM_DATASOURCE, _("datasource")),
            (DATA_FROM_CATCHALL, _("catchall")),
            (DATA_FROM_EXCEPT_CATCHALL, _("except catchall"))
        ],
        default=DATA_FROM_DATASOURCE)

    datasource = models.ForeignKey(
        'flexible_reports.Datasource', verbose_name=_("Datasource"),
        null=True, blank=True)

    table = models.ForeignKey('flexible_reports.Table',
                              verbose_name=_("Table"))
    slug = models.SlugField(max_length=200, verbose_name=_("Slug"))

    def clean(self):
        if self.data_from != DATA_FROM_DATASOURCE:
            if self.datasource is not None:
                raise ValidationError(
                    {"datasource": [ValidationError(
                        _(
                            "In case when data is from catchall or except-catchall, "
                            "please specify an empty datasource."))]})

        if self.data_from == DATA_FROM_DATASOURCE:
            if self.datasource is None:
                raise ValidationError(
                    {"datasource": [ValidationError(
                        _("Please specify a datasource."))]})


    class Meta:
        unique_together = [
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
    _context = None

    @property
    def base_queryset(self):
        if self._base_queryset is None:
            raise ImproperlyConfigured("Please set base queryset for this "
                                       "report using Report.set_base_queryset")
        return self._base_queryset

    @property
    def context(self):
        return self._context

    class Meta:
        verbose_name_plural = _("Reports")
        verbose_name = _("Report")

    def set_base_queryset(self, queryset):
        self._base_queryset = queryset

    def set_context(self, context):
        self._context = context
