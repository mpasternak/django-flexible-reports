# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from .behaviors import Orderable, Labelled


class Column(Labelled, Orderable):
    parent = models.ForeignKey('flexible_reports.Table')

    sortable = models.BooleanField(default=True)

    attr_name = models.CharField(
        verbose_name=_("Attribute name"),
        max_length=200,
        help_text=_("""
        Attribute name on the parent table's base model. 
        
        If this column is sortable, that attribute is used to sort this 
        column. 
        
        In case no value is given in "Template" field, 
        this attribute will be used to get information from model 
        instances.
         
        Warning, if you want to make this column sortable, you need to 
        provide this value.
        
        This value can contain dot notation to reference fields in related 
        models.
        """),
        blank=True, null=True)

    template = models.TextField(
        verbose_name=_("Template"),
        default="{{ value }}",
        null=True,
        blank=True,
        help_text=_("""If empty, the value of the object's attribute from 
        "Attribute name" field will be used instead. 
            
        Template will get following values in it's context:     
        - *record*  -- data record for the current row
        - *value*   -- value from `record` that corresponds to the current column
        - *default* -- appropriate default value to use as fallback
        """))

    display_totals = models.BooleanField(
        default=False,
        verbose_name=_("Display totals"),
        help_text=_("Display column totals in footer. For columns without "
                    "Attribute name, this will be total number of the rows.")
    )

    footer_template = models.TextField(
        verbose_name=_("Footer template"),
        default="{{ value }}",
        blank=True,
        null=True,
        help_text=_("""
        Template for footer.""")
    )

    class Meta:
        unique_together = ('parent', 'id', 'position')
        ordering = ('position',)
        verbose_name = _("Column")
        verbose_name_plural = _("Columns")

    def clean(self):
        parent_model = self.parent.base_model.model_class()

        if self.attr_name:

                path = self.attr_name.split(".")

                current_model = parent_model

                for attr_name in path:
                    try:
                        current_model = getattr(current_model, attr_name)

                        if hasattr(current_model, 'get_queryset'):
                            current_model = current_model.get_queryset().model

                    except Exception as e:
                        raise ValidationError(
                            {"attr_name": [
                                ValidationError(
                                    _("'%(attr_name)s' is not a valid value for base "
                                      "model '%(base_model)s' (exception: %("
                                      "exception)s). "),
                                    params={
                                        "attr_name": self.attr_name,
                                        "base_model": parent_model,
                                        "exception": e
                                    }
                                )]})

        if self.sortable and not self.attr_name:
            raise ValidationError(
                {"attr_name": [
                    ValidationError(
                        _("You marked this column as sortable. You must "
                          "enter value into \"Attribute name\" field. ")
                    )
                ]}
            )

        if not self.attr_name and not self.template:
            raise ValidationError(
                {"attr_name": [
                    ValidationError(
                        _("You must either enter a template for this "
                          "column or an attribute name. "))],
                    "template": [
                        ValidationError(
                            _("You must either enter a template for this "
                              "column or an attribute name. "))

                    ]
                }
            )

        if self.display_totals and not self.footer_template:
            raise ValidationError(
                {'footer_template': [
                    ValidationError(
                        _("If 'Display totals' is enabled, you should "
                          "provide a footer template. Perhaps try with a "
                          "very basic and default one, like '{{ value }}'. ")
                    )
                ]}
            )
