# -*- encoding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django_dsl import compiler, exceptions

from .helpers import SmallerTextarea, AverageTextarea
from .. import utils
from ..models.datasource import Datasource


class DatasourceForm(forms.ModelForm):
    def clean(self):
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
        widgets = {
            'label': SmallerTextarea,
            'dsl_query': AverageTextarea
        }


@admin.register(Datasource)
class DatasourceAdmin(admin.ModelAdmin):
    list_display = ['label', 'base_model', 'dsl_query']
    form = DatasourceForm
