# -*- encoding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.utils.html import format_html

try:
    from django.utils.translation import gettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

from ..models.datasource import Datasource
from .helpers import BiggerTextarea, SmallerTextarea


class DatasourceForm(forms.ModelForm):
    # Validation lives on Datasource.clean(), which dispatches to the query
    # backend selected by ``query_language``; the ModelForm runs it for us.
    class Meta:
        model = Datasource
        fields = [
            "label",
            "base_model",
            "query_language",
            "dsl_query",
            "sample_context",
            "distinct",
        ]
        widgets = {"label": SmallerTextarea, "dsl_query": BiggerTextarea}


@admin.register(Datasource)
class DatasourceAdmin(admin.ModelAdmin):
    list_display = ["label", "base_model", "query_language", "dsl_query_fmt"]
    form = DatasourceForm

    def dsl_query_fmt(self, obj):
        return format_html("<pre>{}</pre>", obj.dsl_query)

    dsl_query_fmt.short_description = _("Query")
