# -*- encoding: utf-8 -*-

import pytest
from django.urls.base import reverse
from flexible_reports.models import Report, Table
from flexible_reports.models.datasource import Datasource


@pytest.mark.parametrize(
    "admin_url,model_class",
    [["table", Table],
     ["report", Report],
     ["datasource", Datasource]]
)
def test_admin(admin_client, admin_url, model_class):
    for elem in ["add", "changelist"]:
        url = reverse(f"admin:flexible_reports_{ admin_url }_{ elem }")
        res = admin_client.get(url)
        assert res.status_code == 200
