# -*- encoding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from flexible_reports.admin.helpers import BiggerTextarea
from .helpers import SmallerTextarea
from .helpers import SortableHiddenMixin
from ..models import Report
from ..models.report import ReportElement


class ReportElementForm(forms.ModelForm):
    class Meta:
        widgets = {
            'title': SmallerTextarea,
        }


class ReportElementInline(SortableHiddenMixin,
                          admin.StackedInline):
    extra = 0

    model = ReportElement

    form = ReportElementForm

    fields = ['title',
              'slug',
              'data_from',
              'datasource',
              'base_model',
              'table',
              'position']

    prepopulated_fields = {'slug': ['title',]}


class ReportForm(forms.ModelForm):
    class Meta:
        widgets = {
            'title': SmallerTextarea,
            'template': BiggerTextarea
        }


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'elements']
    inlines = [ReportElementInline, ]
    form = ReportForm
    prepopulated_fields = {"slug": ("title",)}

    def elements(self, obj):
        return ", ".join([x.title for x in obj.reportelement_set.all()])
    elements.short_description = _("Report's elements")
