# -*- encoding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_dsl import compiler, exceptions

from flexible_reports.admin.helpers import BiggerTextarea
from .helpers import SmallerTextarea
from .. import utils
from ..models.datasource import Datasource


class DatasourceForm(forms.ModelForm):
    def clean(self):
        if 'base_model' not in self.cleaned_data:
            return

        model = self.cleaned_data['base_model'].model_class()
        shortcuts = utils.get_shortcuts(model)

        try:
            filter = compiler.compile(
                self.cleaned_data['dsl_query'],
                shortcuts)
        except exceptions.CompileException:
            return  # handled by dsl_query.validators

        try:
            model.objects.filter(filter).first()
        except Exception as e:
            raise ValidationError(
                {"dsl_query": [
                    ValidationError(
                        _("An error occured while trying to run the actual "
                          "database query (%(error)s)"),
                        params={"error": e}
                    )
                ]}
            )

    class Meta:
        model = Datasource
        fields = ["label", "base_model", "dsl_query", "distinct"]
        widgets = {
            'label': SmallerTextarea,
            'dsl_query': BiggerTextarea
        }


@admin.register(Datasource)
class DatasourceAdmin(admin.ModelAdmin):
    list_display = ['label', 'base_model', 'dsl_query_fmt']
    form = DatasourceForm

    def dsl_query_fmt(self, obj):
        return mark_safe(f"<pre>{ obj.dsl_query }</pre>")

    dsl_query_fmt.short_description = _("DSL query")
