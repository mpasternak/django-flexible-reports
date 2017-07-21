# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Titled


class ReportElement(Orderable):
    parent = models.ForeignKey('flexible_reports.Report')
    datasource = models.ForeignKey('flexible_reports.Datasource')
    table = models.ForeignKey('flexible_reports.Table')

    class Meta:
        unique_together = ('parent', 'position')


class Report(Titled):
    """Report is a collection of multiple Datasources' data
    rendered in Tables. """

    class Meta:
        verbose_name_plural = _("Reports")
        verbose_name = _("Report")
