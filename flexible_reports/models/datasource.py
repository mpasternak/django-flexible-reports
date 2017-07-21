# -*- encoding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_dsl.fields import DjangoDSLField

from .behaviors import Labelled


class Datasource(Labelled):
    """Datasource gets data from the database.

    It uses self.base_model.objects.all(), unless there's something in
    dsl_query field.

    If there is, it compiles that DSL and uses
    self.base_model.objects.filter().
    """

    base_model = models.ForeignKey(
        ContentType,
        verbose_name=_("Base model"),
    )

    dsl_query = DjangoDSLField(
        verbose_name=_("DSL query"))

    class Meta:
        verbose_name = _("Datasource")
        verbose_name_plural = _("Datasources")
