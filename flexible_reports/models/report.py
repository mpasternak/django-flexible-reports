# -*- encoding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Titled
from .validators import TemplateValidator

DATA_FROM_DATASOURCE = 0
DATA_FROM_EXCEPT_CATCHALL = 2

class ReportElement(Titled, Orderable):
    parent = models.ForeignKey('flexible_reports.Report',
                               verbose_name=_("Parent"))
    data_from = models.IntegerField(
        verbose_name=_("Data from"),
        choices=[
            (DATA_FROM_DATASOURCE, _("datasource")),
            (DATA_FROM_EXCEPT_CATCHALL, _("except catchall"))
        ],
        default=DATA_FROM_DATASOURCE)

    datasource = models.ForeignKey(
        'flexible_reports.Datasource',
        verbose_name=_("Datasource"),
        null=True,
        blank=True,
        help_text=_("Fill only if 'datasource' has been chosen in 'Data from' "
                    "field")
    )

    base_model = models.ForeignKey(
        ContentType,
        verbose_name=_("Base model"),
        null=True, blank=True,
        help_text=_(
            "Fill only if 'except catchall' is selected in 'Data from' "
            "field")
    )

    table = models.ForeignKey('flexible_reports.Table',
                              verbose_name=_("Table"))
    slug = models.SlugField(max_length=200, verbose_name=_("Slug"))

    def clean(self):
        if self.data_from != DATA_FROM_DATASOURCE:
            if self.datasource is not None:
                raise ValidationError(
                    {"datasource": [ValidationError(
                        _(
                            "In case when data is from except-catchall, "
                            "please specify an empty datasource."))]})

            if self.base_model is None:
                raise ValidationError(
                    {"base_model": [ValidationError(
                        _(
                            "In case when data is from except-catchall, "
                            "please specify a base model."))]})


        if self.data_from == DATA_FROM_DATASOURCE:
            if self.datasource is None:
                raise ValidationError(
                    {"datasource": [ValidationError(
                        _("Please specify a datasource."))]})

            if self.base_model is not None:
                raise ValidationError(
                    {"base_model": [ValidationError(
                        _("Please specify an empty base model."))]})


    class Meta:
        unique_together = [
            ('parent', 'slug')
        ]
        ordering = ('position',)
        verbose_name = _("Report element")
        verbose_name_plural = _("Report elements")


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
