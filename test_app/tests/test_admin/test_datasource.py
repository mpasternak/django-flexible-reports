import pytest
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from flexible_reports.admin.datasource import DatasourceAdmin, DatasourceForm
from flexible_reports.models.datasource import Datasource
from test_app.models import MyTestFoo


def test_dsl_query_fmt_escapes_html():
    # The query is admin-authored free text; it must be escaped, not marked
    # safe, when shown in the changelist (stored XSS otherwise).
    obj = Datasource(dsl_query="<script>alert(1)</script>")
    html = DatasourceAdmin(Datasource, admin.site).dsl_query_fmt(obj)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


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


@pytest.mark.django_db
def test_datasource_form_blank_sample_context_saves():
    # Regression: clearing "Sample parameters" in the admin submits an empty
    # value, which forms.JSONField turns into None. With the field declared
    # null=False that saved NULL into a NOT NULL column -> IntegrityError (a
    # 500 in the admin). An empty submission must save cleanly.
    form = DatasourceForm(data=_data(sample_context=""))
    assert form.is_valid(), form.errors
    obj = form.save()
    assert obj.pk is not None
