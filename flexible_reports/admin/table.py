# -*- encoding: utf-8 -*-
from django.contrib import admin

from ..models import Table, Column


class ColumnInline(admin.StackedInline):
    model = Column
    fields = ["label", "sortable", "template"]


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['title', 'subtitle']
    inlines = [ColumnInline]
    pass
