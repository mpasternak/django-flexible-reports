# -*- encoding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_dsl import compiler
from django_dsl.exceptions import CompileException
from django_dsl.fields import DjangoDSLField

from .behaviors import Labelled, WithBaseModel


class Datasource(Labelled, WithBaseModel):
    """Datasource gets data from the database.

    It uses self.base_model.objects.all(), unless there's something in
    dsl_query field.

    If there is, it compiles that DSL and uses
    self.base_model.objects.filter().
    """

    dsl_query = DjangoDSLField(
        verbose_name=_("DSL query"))

    class Meta:
        verbose_name = _("Datasource")
        verbose_name_plural = _("Datasources")

    def get_model(self):
        return self.base_model.model_class()

    def get_shortcuts(self):
        return getattr(self.get_model(), 'django_dsl_shortcuts', {})

    def get_filter(self):
        return compiler.compile(
            self.dsl_query,
            shortcuts=self.get_shortcuts())
