import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from model_bakery import baker

from flexible_reports.models.datasource import Datasource
from flexible_reports.models.report import (
    DATA_FROM_EXCEPT_CATCHALL,
    Report,
    ReportElement,
)
from flexible_reports.models.table import SortIndividually, SortInGroup, Table
from test_app.models import MyTestBar, MyTestFoo, MyTestForeign


@pytest.mark.django_db
def test_table():
    t = Table(sort_option=SortInGroup.id, group_prefix=None)

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


def _ct(model):
    return ContentType.objects.get_for_model(model)


@pytest.mark.django_db
def test_get_base_models_unknown_for_a_fresh_table():
    assert Table(label="t").get_base_models() == []
    assert baker.make(Table, base_model=None).get_base_models() == []


@pytest.mark.django_db
def test_get_base_models_falls_back_to_the_stored_model():
    # Tables saved while the form still had the field.
    t = baker.make(Table, base_model=_ct(MyTestFoo))
    assert t.get_base_models() == [MyTestFoo]


@pytest.mark.django_db
def test_get_base_models_falls_back_to_the_default_model(settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = ["test_app.MyTestBar"]
    assert Table(label="t").get_base_models() == [MyTestBar]
    # ...but a stored model is more specific than the project default.
    t = baker.make(Table, base_model=_ct(MyTestFoo))
    assert t.get_base_models() == [MyTestFoo]


@pytest.mark.django_db
def test_get_base_models_comes_from_the_datasources():
    # The datasource decides, even against what the table itself stores.
    t = baker.make(Table, base_model=_ct(MyTestFoo))
    r = baker.make(Report)
    ds = baker.make(Datasource, base_model=_ct(MyTestBar), dsl_query='i = "x"')
    baker.make(ReportElement, parent=r, table=t, datasource=ds)
    assert t.get_base_models() == [MyTestBar]

    # Used with a second model as well: both, in a stable order.
    ds2 = baker.make(Datasource, base_model=_ct(MyTestForeign), dsl_query="i = 5")
    baker.make(ReportElement, parent=r, table=t, datasource=ds2, slug="second")
    assert t.get_base_models() == [MyTestBar, MyTestForeign]


@pytest.mark.django_db
def test_get_base_models_counts_except_catchall_elements():
    t = baker.make(Table, base_model=None)
    r = baker.make(Report)
    baker.make(
        ReportElement,
        parent=r,
        table=t,
        datasource=None,
        data_from=DATA_FROM_EXCEPT_CATCHALL,
        base_model=_ct(MyTestFoo),
    )
    assert t.get_base_models() == [MyTestFoo]
