# -*- encoding: utf-8 -*-

import pytest
from django.contrib.contenttypes.models import ContentType
from model_bakery import baker

from flexible_reports.models import Column, Datasource, Report, ReportElement, Table
from flexible_reports.models.report import (
    DATA_FROM_DATASOURCE,
    DATA_FROM_EXCEPT_CATCHALL,
)
from flexible_reports.models.table import ColumnOrder
from test_app.models import MyTestFoo


@pytest.fixture
def base_model():
    return ContentType.objects.get_for_model(MyTestFoo)


@pytest.fixture
def table(base_model):
    t = baker.make(
        Table,
        label="My table",
        base_model=base_model,
        group_prefix="pfx",
    )
    first = baker.make(
        Column,
        parent=t,
        label="First column",
        attr_name="i",
        position=0,
        template="{{ value }}",
    )
    second = baker.make(
        Column,
        parent=t,
        label="Second column",
        attr_name="i",
        position=1,
        template="{{ value }}!",
    )
    baker.make(ColumnOrder, table=t, column=second, desc=True, position=0)
    baker.make(ColumnOrder, table=t, column=first, desc=False, position=1)
    return t


@pytest.fixture
def report(table, base_model):
    r = baker.make(Report, title="My report", slug="my-report", template="{{ foo }}")
    ds = baker.make(Datasource, base_model=base_model, dsl_query="i > 0")
    baker.make(
        ReportElement,
        parent=r,
        title="First element",
        slug="first-element",
        table=table,
        datasource=ds,
        data_from=DATA_FROM_DATASOURCE,
        position=0,
    )
    return r


@pytest.mark.django_db
def test_clone_table_copies_columns(table):
    clone = table.clone()

    assert clone.pk != table.pk
    assert clone.base_model_id == table.base_model_id
    assert clone.group_prefix == table.group_prefix

    original_columns = list(Column.objects.filter(parent=table).order_by("position"))
    cloned_columns = list(Column.objects.filter(parent=clone).order_by("position"))

    assert len(cloned_columns) == len(original_columns) == 2

    for original, cloned in zip(original_columns, cloned_columns):
        assert cloned.pk != original.pk
        assert cloned.parent_id == clone.pk
        assert cloned.label == original.label
        assert cloned.attr_name == original.attr_name
        assert cloned.template == original.template
        assert cloned.position == original.position


@pytest.mark.django_db
def test_clone_table_remaps_column_order(table):
    clone = table.clone()

    original_orders = list(ColumnOrder.objects.filter(table=table).order_by("position"))
    cloned_orders = list(ColumnOrder.objects.filter(table=clone).order_by("position"))

    assert len(cloned_orders) == len(original_orders) == 2

    cloned_column_pks = set(
        Column.objects.filter(parent=clone).values_list("pk", flat=True)
    )

    for original, cloned in zip(original_orders, cloned_orders):
        # Both foreign keys have to be repointed at the clone.
        assert cloned.table_id == clone.pk
        assert cloned.column_id in cloned_column_pks
        assert cloned.column_id != original.column_id
        # ... and the ordering itself has to be preserved.
        assert cloned.column.label == original.column.label
        assert cloned.desc == original.desc
        assert cloned.position == original.position


@pytest.mark.django_db
def test_clone_table_does_not_touch_source(table):
    # Load the source the way the admin does -- with a prefetched, *cached*
    # related manager. Nulling PKs on cached instances would corrupt objects
    # the caller still holds.
    source = Table.objects.prefetch_related("column_set").get(pk=table.pk)
    cached_columns = list(source.column_set.all())
    original_pk = source.pk
    original_label = source.label
    original_column_pks = [c.pk for c in cached_columns]

    source.clone()

    assert source.pk == original_pk
    assert source.label == original_label
    assert [c.pk for c in cached_columns] == original_column_pks
    # The cached manager must still hand back exactly the source's columns.
    assert [c.pk for c in source.column_set.all()] == original_column_pks
    assert all(c.parent_id == original_pk for c in source.column_set.all())

    # Nothing got moved away from the source in the database either.
    assert Column.objects.filter(parent=source).count() == 2
    assert ColumnOrder.objects.filter(table=source).count() == 2


@pytest.mark.django_db
def test_clone_table_is_independent(table):
    clone = table.clone()

    cloned_column = Column.objects.filter(parent=clone).order_by("position").first()
    cloned_column.label = "Changed label"
    cloned_column.attr_name = "id"
    cloned_column.save()

    original_column = Column.objects.filter(parent=table).order_by("position").first()
    assert original_column.label == "First column"
    assert original_column.attr_name == "i"


@pytest.mark.django_db
def test_clone_table_label_is_numbered(table):
    first = table.clone()
    assert first.label == "My table (copy)"

    second = table.clone()
    assert second.label == "My table (copy 2)"

    # A clone of a clone strips the existing suffix instead of nesting it.
    third = first.clone()
    assert third.label == "My table (copy 3)"


@pytest.mark.django_db
def test_clone_report_shares_tables(report):
    clone = report.clone()

    original_element = ReportElement.objects.get(parent=report)
    cloned_element = ReportElement.objects.get(parent=clone)

    assert cloned_element.pk != original_element.pk
    # Shallow clone: the very same Table and Datasource rows.
    assert cloned_element.table_id == original_element.table_id
    assert cloned_element.datasource_id == original_element.datasource_id
    assert Table.objects.count() == 1
    assert Datasource.objects.count() == 1


@pytest.mark.django_db
def test_clone_report_copies_elements(report, table):
    baker.make(
        ReportElement,
        parent=report,
        title="Second element",
        slug="second-element",
        table=table,
        datasource=Datasource.objects.first(),
        data_from=DATA_FROM_DATASOURCE,
        position=1,
    )

    clone = report.clone()

    assert clone.pk != report.pk
    assert clone.title == "My report (copy)"
    assert clone.template == report.template

    original_elements = list(
        ReportElement.objects.filter(parent=report).order_by("position")
    )
    cloned_elements = list(
        ReportElement.objects.filter(parent=clone).order_by("position")
    )

    assert len(cloned_elements) == len(original_elements) == 2
    # Element slugs stay unchanged -- the copied report template addresses
    # them by slug.
    assert [e.slug for e in cloned_elements] == [e.slug for e in original_elements]
    assert [e.title for e in cloned_elements] == [e.title for e in original_elements]
    assert all(e.parent_id == clone.pk for e in cloned_elements)


@pytest.mark.django_db
def test_clone_report_handles_except_catchall(base_model):
    r = baker.make(Report, title="Catchall report", slug="catchall-report")
    baker.make(
        ReportElement,
        parent=r,
        title="Catchall element",
        slug="catchall-element",
        table=baker.make(Table, label="t", base_model=base_model),
        datasource=None,
        base_model=base_model,
        data_from=DATA_FROM_EXCEPT_CATCHALL,
    )

    clone = r.clone()

    cloned_element = ReportElement.objects.get(parent=clone)
    assert cloned_element.datasource_id is None
    assert cloned_element.base_model_id == base_model.pk
    assert cloned_element.data_from == DATA_FROM_EXCEPT_CATCHALL
    cloned_element.clean()


@pytest.mark.django_db
def test_clone_report_unique_slug():
    max_length = Report._meta.get_field("slug").max_length
    assert max_length == 50

    slug = "a" * 50
    r = baker.make(Report, title="Long slug report", slug=slug)

    clone = r.clone()

    assert clone.slug != r.slug
    assert len(clone.slug) <= max_length
    # The stem gets truncated, never the suffix.
    assert clone.slug.endswith("-copy")

    second = r.clone()
    assert second.slug != clone.slug
    assert len(second.slug) <= max_length
    assert second.slug.endswith("-copy-2")

    assert Report.objects.filter(slug=r.slug).count() == 1
