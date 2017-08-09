# -*- encoding: utf-8 -*-

import pytest
from django.core.exceptions import ValidationError

from flexible_reports.models.validators import TemplateValidator


@pytest.mark.django_db
def test_validators():
    with pytest.raises(ValidationError):
        TemplateValidator("{% for a in b %}")

    TemplateValidator("hi")
