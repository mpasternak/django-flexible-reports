# -*- coding: utf-8 -*-

from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType

try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields.jsonb import JSONField

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.text import format_lazy

try:
    from django.utils.translation import gettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

from .behaviors import Labelled, Orderable
from .cloning import next_free_label


class SortWithOtherTables:
    """prefix = None"""

    id = 0
    label = _("sort with other tables")
    help_text = _(
        """if a column in this table is sorted, all the other tables
    on the page with columns with identical name will be sorted too, as long
    as they also are marked as 'sort with other tables'
    """
    )

    def get_prefix(self, table):
        return ""


class SortIndividually:
    """prefix = self.pk"""

    id = 1
    label = _("sort individually")
    help_text = _(
        """this table will be sorted individually; even if other
    tables on the page have columns with same label this table will be
    sorted independently"""
    )

    def get_prefix(self, table):
        return table.pk


class SortInGroup:
    """prefix = self.group_prefix"""

    id = 2
    label = _("sort in group")
    help_text = _(
        """this table will be sorted together with a group of
    tables; you must enter a prefix for this group"""
    )

    def get_prefix(self, table):
        return table.group_prefix


AllSortOptions = OrderedDict(
    [(x.id, x) for x in [SortWithOtherTables, SortIndividually, SortInGroup]]
)


class ColumnOrder(Orderable):
    table = models.ForeignKey(
        "flexible_reports.Table", verbose_name=_("Table"), on_delete=models.CASCADE
    )
    column = models.ForeignKey(
        "flexible_reports.Column", verbose_name=_("Column"), on_delete=models.CASCADE
    )
    desc = models.BooleanField(_("Descending"), default=False)

    class Meta:
        verbose_name = _("Column order information")
        verbose_name_plural = _("Column order informations")
        ordering = ("position",)

    def get(self):
        if not self.desc:
            return self.column.label
        return f"-{ self.column.label }"


class Table(Labelled):
    """Collection of Columns."""

    base_model = models.ForeignKey(
        ContentType, verbose_name=_("Base model"), on_delete=models.CASCADE
    )

    sort_option = models.IntegerField(
        default=0,
        verbose_name=_("Sort option"),
        choices=[
            (x.id, format_lazy("{label} - {text}", label=x.label, text=x.help_text))
            for x in AllSortOptions.values()
        ],
    )

    attrs = JSONField(verbose_name=_("HTML attributes"), blank=True, null=True)

    group_prefix = models.CharField(
        verbose_name=_("Group prefix"),
        null=True,
        blank=True,
        max_length=200,
        help_text=_(
            """this value is used as a prefix only when "Sort
        option" is set to "sort in group"
        """
        ),
    )

    empty_template = models.TextField(
        verbose_name=_("Empty template"),
        null=True,
        blank=True,
        help_text=_(
            """
        Template which will be displayed when there is no data for this
        table.
        """
        ),
        default=_("There is no data for this table."),
    )

    class Meta:
        verbose_name = _("Table")
        verbose_name_plural = _("Tables")

    def clean(self):
        if self.sort_option == SortInGroup.id:
            if not self.group_prefix:
                raise ValidationError(
                    {
                        "group_prefix": [
                            ValidationError(
                                _(
                                    "Please enter group prefix if you want to sort in "
                                    "group"
                                )
                            )
                        ]
                    }
                )

    def get_prefix(self):
        return AllSortOptions[self.sort_option].get_prefix(None, self)

    def clone(self):
        """Copy this table together with its columns and sort order.

        Returns the newly created :class:`Table`.

        Neither ``self`` nor any object reachable from it is modified: after
        the call ``self.pk`` is unchanged and a subsequent ``self.save()``
        still updates the original. Children are therefore fetched with a
        *fresh* queryset -- going through ``self.column_set`` would hand back
        the instances cached by ``prefetch_related()``, and nulling their
        primary keys would corrupt objects the caller still holds.

        Reports using this table are deliberately left alone.
        """
        from .column import Column

        with transaction.atomic():
            columns = list(Column.objects.filter(parent=self))
            column_orders = list(ColumnOrder.objects.filter(table=self))

            clone = Table.objects.get(pk=self.pk)
            clone.pk = None
            clone._state.adding = True
            clone.label = next_free_label(Table.objects.all(), "label", self.label)
            clone.save()

            # old Column pk -> freshly saved Column
            column_map = {}
            for column in columns:
                old_pk = column.pk
                column.pk = None
                column._state.adding = True
                column.parent = clone
                column.save()
                column_map[old_pk] = column

            for column_order in column_orders:
                old_column_id = column_order.column_id
                column_order.pk = None
                column_order._state.adding = True
                # Both foreign keys have to be repointed. Without ``table``
                # the entry would stay with the original and the clone would
                # silently lose its ordering; without ``column`` the clone
                # would sort by the original's columns.
                column_order.table = clone
                new_column = column_map.get(old_column_id)
                if new_column is not None:
                    column_order.column = new_column
                column_order.save()

            return clone
