from django.core.exceptions import ValidationError
from django.template import Template
from django.utils.translation import gettext_lazy as _


def TemplateValidator(value):
    """Try to compile a string into a Django template"""

    try:
        Template(value)
    except Exception as e:
        raise ValidationError(
            _("Cannot compile template (%(exception)s)"), params={"exception": e}
        )
