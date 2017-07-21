# -*- encoding: utf-8 -*-
from django.contrib import admin

from ..models import Report
from ..models.report import ReportElement

from .helpers import SortableHiddenMixin


class ReportElementInline(
    SortableHiddenMixin,
    admin.TabularInline):
    model = ReportElement
    fields = ['datasource', 'table', 'position']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'subtitle']
    inlines = [ReportElementInline, ]
    pass
