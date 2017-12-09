# -*- encoding: utf-8 -*-
import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ValidationError
from flexible_reports.models.datasource import Datasource
from flexible_reports.models.report import (
    DATA_FROM_DATASOURCE, DATA_FROM_EXCEPT_CATCHALL, Report, ReportElement, get_reports_template,
)
from model_mommy import mommy
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_report():
    r = Report()
    with pytest.raises(ImproperlyConfigured):
        r.base_queryset

    r.set_base_queryset(MyTestFoo.objects.all())
    assert r.base_queryset is not None


def test_get_reports_template():
    assert get_reports_template() is not None


@pytest.mark.django_db
def test_reportelement():
    mtf = ContentType.objects.get_for_model(Report)
    ds = mommy.make(Datasource, base_model=mtf, dsl_query="slug = 'foo'")

    r = mommy.make(Report)

    re = mommy.make(
        ReportElement,
        parent=r,
        data_from=DATA_FROM_EXCEPT_CATCHALL,
        datasource=ds,
        base_model=mtf)
    with pytest.raises(ValidationError):
        re.clean()

    re.datasource = None
    re.clean()

    re = mommy.make(
        ReportElement,
        parent=r,
        data_from=DATA_FROM_DATASOURCE,
        datasource=None,
        base_model=None)
    with pytest.raises(ValidationError):
        re.clean()

    re.base_model = mtf
    re.datasource = ds
    with pytest.raises(ValidationError):
        re.clean()

    re.base_model = None
    re.clean()
