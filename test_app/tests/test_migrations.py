import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from test_app.models import MyTestBar, MyTestFoo

APP = "flexible_reports"
BEFORE = [(APP, "0014_alter_datasource_sample_context")]
LATEST = [(APP, "0016_table_base_model_reverse")]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return MigrationExecutor(connection).loader.project_state(targets).apps


@pytest.fixture
def restore_migrations():
    yield
    _migrate(LATEST)


@pytest.mark.django_db(transaction=True)
def test_rollback_past_0015_fills_missing_table_models(settings, restore_migrations):
    """Tables created on 0.6 have no base model; going back to 0.5 restores
    NOT NULL on that column, so the reverse migration has to supply one."""
    from flexible_reports.models import Datasource, Report, ReportElement, Table

    settings.FLEXIBLE_REPORTS_BASE_MODELS = ["test_app.MyTestFoo"]
    foo = ContentType.objects.get_for_model(MyTestFoo)
    bar = ContentType.objects.get_for_model(MyTestBar)

    unused = Table.objects.create(label="unused")
    used = Table.objects.create(label="used")
    kept = Table.objects.create(label="kept", base_model=bar)
    ds = Datasource.objects.create(label="ds", base_model=bar, dsl_query='i = "x"')
    report = Report.objects.create(title="r", slug="r", template="x")
    ReportElement.objects.create(
        parent=report, title="e", slug="e", datasource=ds, table=used
    )

    old_apps = _migrate(BEFORE)

    OldTable = old_apps.get_model(APP, "Table")
    # From the datasource the table is used with...
    assert OldTable.objects.get(pk=used.pk).base_model_id == bar.pk
    # ...from the project default for a table used nowhere...
    assert OldTable.objects.get(pk=unused.pk).base_model_id == foo.pk
    # ...and a stored model is left alone.
    assert OldTable.objects.get(pk=kept.pk).base_model_id == bar.pk


@pytest.mark.django_db(transaction=True)
def test_rollback_past_0015_explains_what_it_cannot_resolve(restore_migrations):
    from flexible_reports.models import Table

    orphan = Table.objects.create(label="orphan")
    try:
        with pytest.raises(RuntimeError, match="FLEXIBLE_REPORTS_BASE_MODELS"):
            _migrate(BEFORE)
    finally:
        orphan.delete()
