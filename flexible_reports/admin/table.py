# -*- encoding: utf-8 -*-
from django import forms
from django.contrib import admin

from .helpers import SmallerTextarea, AverageTextarea, SortableHiddenMixin
from ..models import Table, Column


class ColumnForm(forms.ModelForm):
    class Meta:
        widgets = {
            'label': SmallerTextarea,
            'template': AverageTextarea
        }


class ColumnInline(SortableHiddenMixin, admin.StackedInline):
    extra = 0
    model = Column
    form = ColumnForm
    fields = ['label', 'template', 'sortable', 'position']


class TableForm(forms.ModelForm):
    class Meta:
        widgets = {
            'label': SmallerTextarea
        }

    pass


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['label']
    inlines = [ColumnInline]
    form = TableForm
