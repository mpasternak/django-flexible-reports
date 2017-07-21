# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Labelled


class Column(Labelled, Orderable):
    parent = models.ForeignKey('flexible_reports.Table')
    sortable = models.BooleanField(default=True)
    template = models.TextField(default="{{ obj.attribute }}")

    class Meta:
        unique_together = ('parent', 'position')
        verbose_name = _("Column")
        verbose_name_plural = _("Columns")
