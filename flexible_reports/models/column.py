# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Labelled


class Column(Labelled, Orderable):
    parent = models.ForeignKey('flexible_reports.Table')
    sortable = models.BooleanField(default=True)
    attr_name = models.CharField(
        verbose_name=_("Attribute name"),
        max_length=200,
        help_text=_("""
        Attribute name on the parent table's model, used to sort and to 
        extract information. """))
    template = models.TextField(default="{{ obj.attribute }}")

    class Meta:
        unique_together = ('parent', 'position')
        ordering = ('position',)
        verbose_name = _("Column")
        verbose_name_plural = _("Columns")

    def clean(self):
        parent_model = self.parent.base_model.model_class()
        try:
            getattr(parent_model, self.attr_name)
        except Exception as e:
            raise ValidationError(
                {"attr_name": [
                    ValidationError(
                        _("'%(attr_name)s' is not a valida value for base "
                          "model '%(base_model)s' (exception: %("
                          "exception)s). "),
                        params={
                            "attr_name": self.attr_name,
                            "base_model": parent_model,
                            "exception": e
                        }
                    )]})

    def as_django_tables2(self):
        from django_tables2.columns.templatecolumn import TemplateColumn

        return (self.label, TemplateColumn(
            verbose_name=self.label,
            orderable=self.sortable,
            template_code=self.template))
