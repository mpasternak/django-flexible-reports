from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _

from .behaviors import Labelled, Orderable


def _related_model(descriptor):
    """Model that a related-object descriptor on a model *class* points at.

    ``Column.clean()`` walks a dotted ``attr_name`` from one model class to the
    next, so it needs the far end of each relation with no instance to hand.
    The way this used to be obtained -- ``descriptor.get_queryset().model`` --
    stopped working in Django 6.1, where ``get_queryset()`` grew a mandatory
    ``instance`` keyword argument and so can no longer be called off the class.
    The relation metadata holds the same answer and reads the same on Django
    5.2, 6.0 and 6.1.

    Returns ``None`` for anything that is not a relation to follow, in which
    case the caller keeps the attribute itself.
    """
    # Reverse one-to-one: ``related`` is the OneToOneRel, and its
    # ``related_model`` is the model declaring the field, i.e. where the
    # accessor lands.
    related = getattr(descriptor, "related", None)
    if related is not None:
        return getattr(related, "related_model", None)

    # Reverse FK and many-to-many descriptors carry a ``field`` too, but it
    # points back at the model we came from rather than at the far end; only
    # they have ``rel``, which is what tells them apart from the forward ones.
    if hasattr(descriptor, "rel"):
        return None

    # Forward foreign key / one-to-one.
    return getattr(getattr(descriptor, "field", None), "related_model", None)


class Column(Labelled, Orderable):
    parent = models.ForeignKey("flexible_reports.Table", on_delete=models.CASCADE)

    sortable = models.BooleanField(verbose_name=_("Sortable"), default=True)

    attr_name = models.CharField(
        verbose_name=_("Attribute name"),
        max_length=200,
        help_text=_(
            """
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
        """
        ),
        blank=True,
        null=True,
    )

    template = models.TextField(
        verbose_name=_("Template"),
        default="{{ value }}",
        null=True,
        blank=True,
        help_text=_(
            """If empty, the value of the object's attribute from
        "Attribute name" field will be used instead.

        Template will get following values in it's context:
        - *record*  -- data record for the current row
        - *value*   -- value from `record` that corresponds to the current column
        - *default* -- appropriate default value to use as fallback
        """
        ),
    )

    attrs = JSONField(verbose_name=_("HTML attributes"), blank=True, null=True)

    display_totals = models.BooleanField(
        default=False,
        verbose_name=_("Display totals"),
        help_text=_(
            "Display column totals in footer. For columns without "
            "Attribute name, this will be total number of the rows."
        ),
    )

    strip_html_on_export = models.BooleanField(
        default=True,
        verbose_name=_("Strip HTML on export"),
        help_text=_(
            """Strip HTML tags when exporting to other, non-browser
        formats, like MS Word or MS Excel. """
        ),
    )

    exclude_from_export = models.BooleanField(
        default=False,
        verbose_name=_("Exclude from export"),
        help_text=_(
            "Exclude this column when exporting to other, non-browser"
            "formats, like MS Word or MS Excel"
        ),
    )

    footer_template = models.TextField(
        verbose_name=_("Footer template"),
        default="{{ value }}",
        blank=True,
        null=True,
        help_text=_(
            """
        Template for footer. Used only if "Display totals" is enabled. It is
        rendered with 3 variables:
        - *count* -- total count of rows in the table,
        - *value* -- sum of this column's values (or row count if non-numeric),
        - *error* -- string representation of exception in case an exception
        occurs during addition of column's values.

        So, if the column values are numbers, just use {{ value }}. If you want
        to output number of rows, just use {{ count }}. """
        ),
    )

    class Meta:
        unique_together = ("parent", "id", "position")
        ordering = ("position",)
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

                    related_model = _related_model(current_model)
                    if related_model is not None:
                        current_model = related_model

                except Exception as e:
                    raise ValidationError(
                        {
                            "attr_name": [
                                ValidationError(
                                    _(
                                        "'%(attr_name)s' is not a valid value for base "
                                        "model '%(base_model)s' (exception: %("
                                        "exception)s). "
                                    ),
                                    params={
                                        "attr_name": self.attr_name,
                                        "base_model": parent_model,
                                        "exception": e,
                                    },
                                )
                            ]
                        }
                    )

        if self.sortable and not self.attr_name:
            raise ValidationError(
                {
                    "attr_name": [
                        ValidationError(
                            _(
                                "You marked this column as sortable. You must "
                                'enter value into "Attribute name" field. '
                            )
                        )
                    ]
                }
            )

        if not self.attr_name and not self.template:
            raise ValidationError(
                {
                    "attr_name": [
                        ValidationError(
                            _(
                                "You must either enter a template for this "
                                "column or an attribute name. "
                            )
                        )
                    ],
                    "template": [
                        ValidationError(
                            _(
                                "You must either enter a template for this "
                                "column or an attribute name. "
                            )
                        )
                    ],
                }
            )  # noqa

        if self.display_totals and not self.footer_template:
            raise ValidationError(
                {
                    "footer_template": [
                        ValidationError(
                            _(
                                "If 'Display totals' is enabled, you should "
                                "provide a footer template. Perhaps try with a "
                                "very basic and default one, like '{{ value }}'. "
                            )
                        )
                    ]
                }
            )
