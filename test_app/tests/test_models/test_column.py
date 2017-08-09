# -*- encoding: utf-8 -*-

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from flexible_reports.models.column import Column
from flexible_reports.models.table import Table
from model_mommy import mommy

from test_app.models import MyTestFoo, MyTestForeign


@pytest.mark.django_db
def test_column():
    t = Table(base_model=ContentType.objects.get_for_model(MyTestFoo))
    c = Column(parent=t)
    c.attr_name = "z"

    with pytest.raises(ValidationError):
        c.clean()

    c.attr_name = "i"
    c.clean()

    c.attr_name = None
    c.sortable = True
    with pytest.raises(ValidationError):
        c.clean()

    c.attr_name = None
    c.template = None
    c.sortable = False
    with pytest.raises(ValidationError):
        c.clean()

    c.attr_name = "i"
    c.footer_template = None
    c.display_totals = True
    with pytest.raises(ValidationError):
        c.clean()



@pytest.mark.django_db
def test_column_foreign():
    t = Table(base_model=ContentType.objects.get_for_model(MyTestForeign))
    c = Column(parent=t)
    c.attr_name = "parent.fobar"

    with pytest.raises(ValidationError):
        c.clean()

    c.attr_name = "parent.i"
    c.clean()
