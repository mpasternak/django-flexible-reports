# -*- encoding: utf-8 -*-

import pytest
from django.contrib.contenttypes.models import ContentType
from flexible_reports.models.datasource import Datasource
from test_app.models import MyTestFoo, MyTestForeign


@pytest.mark.django_db
def test_datasource():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        dsl_query="i=5"
    )

    assert d.get_model() == MyTestFoo
    assert str(d.get_filter()) == "(AND: ('i', 5))"


@pytest.mark.django_db
def test_datasource_foreign():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestForeign),
        dsl_query="i=5"

    )

    assert "i" in d.get_shortcuts()
