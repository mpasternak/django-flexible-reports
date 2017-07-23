# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .behaviors import Labelled


class Table(Labelled):
    """Collection of Columns."""

    base_model = models.ForeignKey(ContentType)

    class Meta:
        verbose_name = _("Table")
        verbose_name_plural = _("Tables")

    def as_django_tables2(self, object_list):
        from django_tables2.tables import Table as DjT2_Table

        extra_columns = []
        for column in self.column_set.all():
            extra_columns.append(column.as_django_tables2())

        return DjT2_Table(
            data=object_list,
            extra_columns=extra_columns)
