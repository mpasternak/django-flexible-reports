# -*- encoding: utf-8 -*-
import pytest
from django.core.exceptions import ValidationError

from flexible_reports.query_backends import (
    DjangoQLQueryBackend,
    DSLQueryBackend,
    get_backend,
)
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_dsl_filter_queryset():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    qs = DSLQueryBackend().filter_queryset(MyTestFoo.objects.all(), "i = 5")
    assert sorted(o.i for o in qs) == [5]


@pytest.mark.django_db
def test_djangoql_filter_queryset():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    qs = DjangoQLQueryBackend().filter_queryset(MyTestFoo.objects.all(), "i = 5")
    assert sorted(o.i for o in qs) == [5]


@pytest.mark.django_db
def test_djangoql_filter_queryset_uses_template_context():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    qs = DjangoQLQueryBackend().filter_queryset(
        MyTestFoo.objects.all(), "i = {{ value }}", context={"value": 7}
    )
    assert sorted(o.i for o in qs) == [7]


@pytest.mark.django_db
def test_dsl_validate_unknown_field_raises():
    with pytest.raises(ValidationError):
        DSLQueryBackend().validate("nope > 1", MyTestFoo)


@pytest.mark.django_db
def test_djangoql_validate_unknown_field_raises():
    with pytest.raises(ValidationError):
        DjangoQLQueryBackend().validate("nope = 1", MyTestFoo)


def test_djangoql_validate_empty_raises():
    with pytest.raises(ValidationError):
        DjangoQLQueryBackend().validate("   ", MyTestFoo)


def test_djangoql_get_filter_not_supported():
    with pytest.raises(NotImplementedError):
        DjangoQLQueryBackend().get_filter("i = 5", MyTestFoo)


def test_get_backend_returns_expected_types():
    assert isinstance(get_backend("dsl"), DSLQueryBackend)
    assert isinstance(get_backend("djangoql"), DjangoQLQueryBackend)


def test_dsl_validate_empty_raises():
    with pytest.raises(ValidationError):
        DSLQueryBackend().validate("   ", MyTestFoo)


@pytest.mark.django_db
def test_dsl_filter_queryset_uses_template_context():
    MyTestFoo.objects.create(i=5)
    MyTestFoo.objects.create(i=7)
    qs = DSLQueryBackend().filter_queryset(
        MyTestFoo.objects.all(), "i = {{ value }}", context={"value": 7}
    )
    assert sorted(o.i for o in qs) == [7]


@pytest.mark.django_db
def test_djangoql_validate_parametrized_with_context_ok():
    DjangoQLQueryBackend().validate("i = {{ value }}", MyTestFoo, context={"value": 5})


@pytest.mark.django_db
def test_djangoql_validate_parametrized_without_context_raises():
    with pytest.raises(ValidationError):
        DjangoQLQueryBackend().validate("i = {{ value }}", MyTestFoo)


@pytest.mark.django_db
def test_dsl_validate_parametrized_with_context_ok():
    DSLQueryBackend().validate("i = {{ value }}", MyTestFoo, context={"value": 5})


@pytest.mark.django_db
def test_dsl_validate_parametrized_without_context_raises():
    with pytest.raises(ValidationError):
        DSLQueryBackend().validate("i = {{ value }}", MyTestFoo)
