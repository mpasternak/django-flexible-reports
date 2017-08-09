# -*- encoding: utf-8 -*-

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls.base import reverse
from model_mommy import mommy

from flexible_reports.models.datasource import Datasource
from flexible_reports.models.report import Report, ReportElement
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_report(admin_client):
    r = mommy.make(Report)
    ds = mommy.make(Datasource,
                    base_model=ContentType.objects.get_for_model(MyTestFoo),
                    dsl_query="i=5")
    re = mommy.make(ReportElement,
                    datasource=ds,
                    parent=r)

    res = admin_client.get(
        reverse("admin:flexible_reports_report_changelist")
    )