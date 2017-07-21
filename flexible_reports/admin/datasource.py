# -*- encoding: utf-8 -*-

from django.contrib import admin

from ..models.datasource import Datasource


@admin.register(Datasource)
class DatasourceAdmin(admin.ModelAdmin):
    list_display = ['label', 'base_model', 'dsl_query']
    pass
