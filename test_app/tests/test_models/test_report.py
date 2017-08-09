# -*- encoding: utf-8 -*-

import pytest
from django.core.exceptions import ImproperlyConfigured

from flexible_reports.models.report import Report, get_reports_template
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
