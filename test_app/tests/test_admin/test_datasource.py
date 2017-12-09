# -*- encoding: utf-8 -*-
import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from flexible_reports.admin.datasource import DatasourceForm
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_datasource_form():
    d = DatasourceForm()

    d.cleaned_data = {}
    assert d.clean() is None

    d.cleaned_data = {
        'base_model': ContentType.objects.get_for_model(MyTestFoo),
        'dsl_query': "134ads"
    }
    assert d.clean() is None

    d.cleaned_data = {
        'base_model': ContentType.objects.get_for_model(MyTestFoo),
        'dsl_query': "x>100"
    }
    with pytest.raises(ValidationError):
        d.clean()
