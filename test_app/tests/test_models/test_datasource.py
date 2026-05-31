# -*- encoding: utf-8 -*-

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from flexible_reports.models.datasource import Datasource
from test_app.models import MyTestFoo, MyTestForeign


@pytest.mark.django_db
def test_datasource():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo), dsl_query="i=5"
    )

    assert d.get_model() == MyTestFoo
    assert str(d.get_filter()) == "(AND: ('i', 5))"


@pytest.mark.django_db
def test_datasource_foreign():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestForeign), dsl_query="i=5"
    )

    assert "i" in d.get_shortcuts()


@pytest.mark.django_db
def test_datasource_filter_queryset_dsl():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="dsl",
        dsl_query="i = 5",
    )
    assert sorted(o.i for o in d.filter_queryset(MyTestFoo.objects.all())) == [5]


@pytest.mark.django_db
def test_datasource_filter_queryset_djangoql():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="djangoql",
        dsl_query="i = 5",
    )
    assert sorted(o.i for o in d.filter_queryset(MyTestFoo.objects.all())) == [5]


@pytest.mark.django_db
def test_datasource_clean_djangoql_ok():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="djangoql",
        dsl_query="i = 5",
    )
    d.clean()  # must not raise


@pytest.mark.django_db
def test_datasource_clean_djangoql_unknown_field_raises():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="djangoql",
        dsl_query="nope = 1",
    )
    with pytest.raises(ValidationError):
        d.clean()


@pytest.mark.django_db
def test_datasource_clean_dsl_ok():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="dsl",
        dsl_query="i = 5",
    )
    d.clean()  # must not raise


@pytest.mark.django_db
def test_datasource_clean_dsl_unknown_field_raises():
    d = Datasource(
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        query_language="dsl",
        dsl_query="nope > 1",
    )
    with pytest.raises(ValidationError):
        d.clean()


def test_datasource_clean_without_base_model_is_noop():
    # base_model is unset -> clean() returns early without touching the DB.
    Datasource(dsl_query="anything").clean()  # must not raise
