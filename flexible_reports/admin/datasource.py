# -*- encoding: utf-8 -*-

from django import forms
from django.contrib import admin

from .helpers import SmallerTextarea, AverageTextarea
from ..models.datasource import Datasource


class DatasourceForm(forms.ModelForm):
    class Meta:
        widgets = {
            'label': SmallerTextarea,
            'dsl_query': AverageTextarea
        }


@admin.register(Datasource)
class DatasourceAdmin(admin.ModelAdmin):
    list_display = ['label', 'base_model', 'dsl_query']
    form = DatasourceForm
