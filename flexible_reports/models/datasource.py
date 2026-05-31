# -*- encoding: utf-8 -*-
from django.db import models

try:
    from django.utils.translation import gettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

from .. import utils
from ..query_backends import DSL, QUERY_LANGUAGE_CHOICES, get_backend
from .behaviors import Labelled, WithBaseModel


class Datasource(Labelled, WithBaseModel):
    """Datasource gets data from the database.

    It narrows ``self.base_model.objects.all()`` using the query stored in
    ``dsl_query``, interpreted according to ``query_language`` (django-dsl or
    DjangoQL).
    """

    query_language = models.CharField(
        max_length=16,
        choices=QUERY_LANGUAGE_CHOICES,
        default=DSL,
        verbose_name=_("Query language"),
    )

    dsl_query = models.TextField(verbose_name=_("Query"))

    sample_context = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Sample parameters"),
        help_text=_(
            "Example values for template parameters in the query "
            '(e.g. {"value": 7}). Used only to validate the query on save.'
        ),
    )

    distinct = models.BooleanField(
        default=True,
        verbose_name=_("Distinct"),
        help_text=_("Output only distinct records"),
    )

    class Meta:
        verbose_name = _("Datasource")
        verbose_name_plural = _("Datasources")
        ordering = ("label",)

    def get_model(self):
        return self.base_model.model_class()

    def get_shortcuts(self):
        return utils.get_shortcuts(self.get_model())

    def get_backend(self):
        return get_backend(self.query_language)

    def get_filter(self, context=None):
        """Return a ``Q`` object for the query.

        Only the django-dsl backend can produce a ``Q``; the DjangoQL backend
        raises ``NotImplementedError`` (use :meth:`filter_queryset` instead).
        """
        return self.get_backend().get_filter(self.dsl_query, self.get_model(), context)

    def filter_queryset(self, base_queryset, context=None):
        """Return ``base_queryset`` narrowed by this datasource's query."""
        return self.get_backend().filter_queryset(
            base_queryset, self.dsl_query, context
        )

    def clean(self):
        if self.base_model_id is None:
            return
        self.get_backend().validate(
            self.dsl_query, self.get_model(), context=self.sample_context
        )
