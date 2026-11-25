import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from flexible_reports.models.column import Column
from flexible_reports.models.table import Table
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


@pytest.mark.django_db
def test_column_without_a_known_model_is_not_checked():
    # A table that is not part of any report and stores no model: there is
    # nothing to resolve the attribute against yet, so it is accepted.
    c = Column(parent=Table(label="t"), attr_name="anything.at_all")
    c.clean()


@pytest.mark.django_db
def test_column_is_checked_against_the_datasource_model():
    from model_bakery import baker

    from flexible_reports.models.datasource import Datasource
    from flexible_reports.models.report import Report, ReportElement

    foreign = ContentType.objects.get_for_model(MyTestForeign)
    # The table itself still stores another model -- the datasource wins.
    t = baker.make(Table, base_model=ContentType.objects.get_for_model(MyTestFoo))
    ds = baker.make(Datasource, base_model=foreign, dsl_query="i = 5")
    baker.make(ReportElement, parent=baker.make(Report), table=t, datasource=ds)

    Column(parent=t, attr_name="parent.i").clean()
    with pytest.raises(ValidationError):
        # Valid on MyTestFoo, which the table is no longer rendered with.
        Column(parent=t, attr_name="i").clean()


@pytest.mark.django_db
def test_column_is_checked_against_the_default_model(settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = ["test_app.MyTestFoo"]
    Column(parent=Table(label="t"), attr_name="i").clean()
    with pytest.raises(ValidationError):
        Column(parent=Table(label="t"), attr_name="nope").clean()
