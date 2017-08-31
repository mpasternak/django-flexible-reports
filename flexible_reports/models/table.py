# -*- coding: utf-8 -*-

from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields.jsonb import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _, string_concat

from .behaviors import Labelled, Orderable


class SortWithOtherTables:
    """prefix = None"""
    id = 0
    label = _("sort with other tables")
    help_text = _("""if a column in this table is sorted, all the other tables
    on the page with columns with identical name will be sorted too, as long
    as they also are marked as 'sort with other tables'
    """)

    def get_prefix(self, table):
        return ""


class SortIndividually:
    """prefix = self.pk"""

    id = 1
    label = _("sort individually")
    help_text = _("""this table will be sorted individually; even if other
    tables on the page have columns with same label this table will be
    sorted independently""")

    def get_prefix(self, table):
        return table.pk


class SortInGroup:
    """prefix = self.group_prefix"""
    id = 2
    label = _("sort in group")
    help_text = _("""this table will be sorted together with a group of
    tables; you must enter a prefix for this group""")

    def get_prefix(self, table):
        return table.group_prefix


AllSortOptions = OrderedDict(
    [(x.id, x) for x in [SortWithOtherTables,
                         SortIndividually,
                         SortInGroup]])


class ColumnOrder(Orderable):
    table = models.ForeignKey("flexible_reports.Table",
                              verbose_name=_("Table"))
    column = models.ForeignKey("flexible_reports.Column",
                               verbose_name=_("Column"))
    desc = models.BooleanField(
        _("Descending"),
        default=False
    )

    class Meta:
        verbose_name = _("Column order information")
        verbose_name_plural = _("Column order informations")
        ordering = ('position',)

    def get(self):
        if not self.desc:
            return self.column.label
        return f"-{ self.column.label }"


class Table(Labelled):
    """Collection of Columns."""

    base_model = models.ForeignKey(
        ContentType,
        verbose_name=_("Base model"))

    sort_option = models.IntegerField(
        default=0,
        verbose_name=_("Sort option"),
        choices=[
            (x.id, string_concat(x.label, " - ", x.help_text))
            for x in AllSortOptions.values()
        ],
    )

    attrs = JSONField(
        verbose_name=_("HTML attributes"),
        blank=True,
        null=True
    )

    group_prefix = models.CharField(
        verbose_name=_("Group prefix"),
        null=True,
        blank=True,
        max_length=200,
        help_text=_("""this value is used as a prefix only when "Sort
        option" is set to "sort in group"
        """))

    empty_template = models.TextField(
        verbose_name=_("Empty template"),
        null=True,
        blank=True,
        help_text=_("""
        Template which will be displayed when there is no data for this
        table.
        """),
        default=_("There is no data for this table.")
    )

    class Meta:
        verbose_name = _("Table")
        verbose_name_plural = _("Tables")

    def clean(self):
        if self.sort_option == SortInGroup.id:
            if not self.group_prefix:
                raise ValidationError({
                    "group_prefix": [ValidationError(
                        _("Please enter group prefix if you want to sort in "
                          "group")
                    )]
                })

    def get_prefix(self):
        return AllSortOptions[self.sort_option].get_prefix(None, self)
