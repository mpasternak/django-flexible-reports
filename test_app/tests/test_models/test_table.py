# -*- encoding: utf-8 -*-

import pytest
from django.core.exceptions import ValidationError

from flexible_reports.models.table import SortInGroup, Table, SortIndividually


@pytest.mark.django_db
def test_table():
    t = Table(
        sort_option=SortInGroup.id,
        group_prefix=None)

    with pytest.raises(ValidationError):
        t.clean()

    t.group_prefix = "foobar"
    t.clean()

def test_sortoptions():
    t = Table(pk=5, group_prefix="foo")

    a = SortIndividually()
    assert a.get_prefix(t) == 5

    a = SortInGroup()
    assert a.get_prefix(t) == "foo"
