# -*- encoding: utf-8 -*-
import pytest
from django.contrib.contenttypes.models import ContentType

from flexible_reports.admin.datasource import DatasourceForm
from test_app.models import MyTestFoo


def _data(**over):
    data = {
        "label": "ds",
        "base_model": ContentType.objects.get_for_model(MyTestFoo).pk,
        "query_language": "dsl",
        "dsl_query": "i = 5",
        "distinct": True,
    }
    data.update(over)
    return data


@pytest.mark.django_db
def test_datasource_form_has_query_language():
    assert "query_language" in DatasourceForm().fields


@pytest.mark.django_db
def test_datasource_form_valid_dsl():
    form = DatasourceForm(data=_data())
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_datasource_form_invalid_dsl_db_error():
    form = DatasourceForm(data=_data(dsl_query="x > 100"))
    assert not form.is_valid()
    assert "dsl_query" in form.errors


@pytest.mark.django_db
def test_datasource_form_valid_djangoql():
    form = DatasourceForm(data=_data(query_language="djangoql", dsl_query="i = 5"))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_datasource_form_invalid_djangoql_unknown_field():
    form = DatasourceForm(data=_data(query_language="djangoql", dsl_query="nope = 1"))
    assert not form.is_valid()
    assert "dsl_query" in form.errors


@pytest.mark.django_db
def test_query_language_dispatch_dsl_rejects_lowercase_or():
    # django-dsl requires uppercase OR; lowercase 'or' is a compile error.
    # Proves the DSL backend is selected when query_language='dsl'.
    form = DatasourceForm(data=_data(query_language="dsl", dsl_query="i = 5 or i = 6"))
    assert not form.is_valid()
    assert "dsl_query" in form.errors


@pytest.mark.django_db
def test_query_language_dispatch_djangoql_accepts_lowercase_or():
    # DjangoQL accepts lowercase 'or'. Proves the DjangoQL backend is selected
    # when query_language='djangoql' (the same query is rejected by DSL above).
    form = DatasourceForm(
        data=_data(query_language="djangoql", dsl_query="i = 5 or i = 6")
    )
    assert form.is_valid(), form.errors
