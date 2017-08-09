# -*- encoding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.utils.translation import string_concat
from django.utils.translation import ugettext_lazy as _

from flexible_reports.models.table import AllSortOptions, SortInGroup
from .helpers import SmallerTextarea, AverageTextarea, SortableHiddenMixin
from ..models import Table, Column


class ColumnForm(forms.ModelForm):
    class Meta:
        widgets = {
            'label': SmallerTextarea,
            'template': AverageTextarea,
            'footer_template': SmallerTextarea
        }


class ColumnInline(SortableHiddenMixin, admin.StackedInline):
    extra = 0
    model = Column
    form = ColumnForm
    fields = ['label',
              'attr_name',
              'template',
              'sortable',
              'display_totals',
              'footer_template',
              'position']


class TableForm(forms.ModelForm):
    class Meta:
        fields = ['label', 'base_model', 'sort_option', 'group_prefix',
                  'empty_template']
        widgets = {
            'label': SmallerTextarea,
            'empty_template': SmallerTextarea
        }

    pass


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['label',
                    'base_model',
                    'short_sort_option',
                    'columns']
    inlines = [ColumnInline]
    form = TableForm

    def columns(self, obj):
        return ", ".join([x.label for x in obj.column_set.all()])

    columns.short_description = _("Columns")

    def short_sort_option(self, obj):
        if obj.sort_option == SortInGroup.id:
            return string_concat(
                SortInGroup.label,
                _(" (group name: "),
                obj.group_prefix,
                ")"
            )
        return AllSortOptions[obj.sort_option].label

    short_sort_option.short_description = _("Sort option")
    short_sort_option.admin_order_field = "sort_option"
