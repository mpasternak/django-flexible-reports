# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from .behaviors import Labelled


class Table(Labelled):
    """Collection of Columns."""

    class Meta:
        verbose_name = _("Table")
        verbose_name_plural = _("Tables")
