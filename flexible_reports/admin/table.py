# -*- encoding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.utils.translation import string_concat
from django.utils.translation import ugettext_lazy as _

from flexible_reports.models.table import AllSortOptions, SortInGroup
from .helpers import SmallerTextarea, AverageTextarea, SortableHiddenMixin
from ..models import Table, Column, ColumnOrder


class ColumnForm(forms.ModelForm):
    class Meta:
        widgets = {
            'label': SmallerTextarea,
            'template': AverageTextarea,
            'footer_template': SmallerTextarea,
            'attrs': SmallerTextarea
        }


class ColumnOrderForm(forms.ModelForm):
    def __init__(self, parent, *args, **kw):
        super(ColumnOrderForm, self).__init__(*args, **kw)
        self.fields['column'].queryset = Column.objects.filter(parent=parent)


class ColumnOrderInline(SortableHiddenMixin, admin.TabularInline):
    extra = 0
    model = ColumnOrder
    fields = ['column', 'desc', 'position']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(ColumnOrderInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'column':
            if request._parent_ is not None:
                field.queryset = field.queryset.filter(
                    parent=request._parent_,
                    sortable=True)

            else:
                field.queryset = field.queryset.none()
        return field


class ColumnInline(SortableHiddenMixin, admin.StackedInline):
    extra = 0
    model = Column
    form = ColumnForm
    fields = ['label',
              'attr_name',
              'template',
              'attrs',
              'sortable',
              'exclude_from_export',
              'strip_html_on_export',
              'display_totals',
              'footer_template',
              'position']


class TableForm(forms.ModelForm):
    class Meta:
        fields = ['label',
                  'base_model',
                  'sort_option',
                  'group_prefix',
                  'attrs',
                  'empty_template',
                  ]
        widgets = {
            'label': SmallerTextarea,
            'empty_template': SmallerTextarea,
            'attrs': SmallerTextarea
        }

    pass


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['label',
                    'base_model',
                    'short_sort_option',
                    'columns']
    inlines = [ColumnInline, ColumnOrderInline]
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

    def get_form(self, request, obj=None, **kwargs):
        request._parent_ = obj
        return super(TableAdmin, self).get_form(request, obj, **kwargs)
