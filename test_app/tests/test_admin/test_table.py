# -*- encoding: utf-8 -*-

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls.base import reverse
from flexible_reports.models.table import SortIndividually, SortInGroup, Table
from model_bakery import baker
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_table(admin_client):
    PREFIX = "this is my prefix"

    t = baker.bake(Table,
                   sort_option=SortInGroup.id,
                   group_prefix=PREFIX,
                   base_model=ContentType.objects.get_for_model(MyTestFoo))

    res = admin_client.get(
        reverse("admin:flexible_reports_table_changelist")
    )
    assert PREFIX in res.rendered_content

    t.sort_option = SortIndividually.id
    t.save()
    res = admin_client.get(
        reverse("admin:flexible_reports_table_changelist")
    )
    assert PREFIX not in res.rendered_content
