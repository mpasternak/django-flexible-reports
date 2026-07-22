# -*- encoding: utf-8 -*-
import re
import threading

import pytest
from bs4 import BeautifulSoup
from django.contrib.contenttypes.models import ContentType
from django.template.base import Template
from django.template.context import RequestContext
from model_bakery import baker

from flexible_reports.adapters import django_tables2
from flexible_reports.models import Column, Datasource, Report, ReportElement, Table
from flexible_reports.models.report import (
    DATA_FROM_DATASOURCE,
    DATA_FROM_EXCEPT_CATCHALL,
)
from test_app.models import MyTestBar

from ..models import MyTestFoo


@pytest.fixture(autouse=True)
def clear_compiled_template_cache():
    # A cached Template remembers the engine active when it was compiled, so
    # the cache must not be carried between tests (override_settings(TEMPLATES)
    # would otherwise be served templates bound to the previous engine).
    django_tables2._compiled_template.cache_clear()
    yield
    django_tables2._compiled_template.cache_clear()


def _build_report(column_labels, column_template="{{ value }}", values=(1, 2, 3)):
    """Build a one-element report over ``MyTestFoo``.

    Returns a (report, table, columns) tuple.
    """
    mtf = ContentType.objects.get_for_model(MyTestFoo)

    for value in values:
        baker.make(MyTestFoo, i=value)

    r = baker.make(Report, title="Report title")
    t = baker.make(Table, label="table", base_model=mtf)

    columns = [
        baker.make(
            Column,
            label=label,
            parent=t,
            attr_name="i",
            template=column_template,
            position=position,
        )
        for position, label in enumerate(column_labels)
    ]

    ds = baker.make(Datasource, base_model=mtf, dsl_query="i > 0")
    baker.make(
        ReportElement,
        title="Report element title",
        slug="element",
        table=t,
        parent=r,
        datasource=ds,
        data_from=DATA_FROM_DATASOURCE,
    )

    r.set_base_queryset(MyTestFoo.objects.all())

    return r, t, columns


@pytest.mark.django_db
def test_label_change_visible_without_restart(rf):
    # Regression: the table class used to be cached per Table.pk for the
    # lifetime of the process, so a label edited in the database was invisible
    # until the process restarted.
    r, t, columns = _build_report(["Old label"])

    request = rf.get("/")

    first = django_tables2.as_html(r, RequestContext(request, dict(request=request)))
    assert "Old label" in first

    Column.objects.filter(pk=columns[0].pk).update(label="New label")

    second = django_tables2.as_html(r, RequestContext(request, dict(request=request)))
    assert "New label" in second
    assert "Old label" not in second


@pytest.mark.django_db
def test_removed_column_disappears(rf):
    # Regression: a column removed from the database stayed in the cached
    # class' ``base_columns`` and kept being rendered.
    r, t, columns = _build_report(["Keep me", "Delete me"])

    request = rf.get("/")

    first = django_tables2.as_html(r, RequestContext(request, dict(request=request)))
    assert "Keep me" in first
    assert "Delete me" in first

    columns[1].delete()

    second = django_tables2.as_html(r, RequestContext(request, dict(request=request)))
    assert "Keep me" in second
    assert "Delete me" not in second


@pytest.mark.django_db
def test_template_column_context_is_complete(rf):
    # The overridden TemplateColumn.render must provide the very same context
    # as the parent implementation: the page context of the template that
    # called {% render_table %}, the record, the value and the row counter.
    r, t, columns = _build_report(
        ["Cell"],
        column_template=(
            "[{{ row_counter }}|{{ record.i }}|{{ value }}|{{ page_variable }}]"
        ),
        values=(11, 22, 33),
    )

    request = rf.get("/")
    ctx = RequestContext(request, dict(request=request, page_variable="from-page"))

    render_context = django_tables2._report(r, ctx)
    html = Template(r.template).render(render_context)

    cells = re.findall(r"\[(.*?)\]", html)
    assert len(cells) == 3

    row_counters = []
    for cell in cells:
        row_counter, record_value, value, page_variable = cell.split("|")
        row_counters.append(row_counter)
        assert record_value == value
        assert record_value in ("11", "22", "33")
        assert page_variable == "from-page"

    # Every row must get its own counter -- proof that ``bound_row`` reaches
    # ``get_context_data``.
    assert sorted(row_counters) == ["0", "1", "2"]

    # The cell variables have to be popped from the page context once the cell
    # has been rendered; ``parent_context.update()`` is used as a context
    # manager precisely for that.
    for leaked in ("row_counter", "record", "value", "column", "default"):
        assert leaked not in render_context


@pytest.mark.django_db
def test_no_template_pinned_to_column(rf):
    # Columns live in ``Table.base_columns`` and are deep-copied on every table
    # instantiation. A compiled ``Template`` references the template engine, so
    # pinning one onto a column would deep-copy the whole engine graph.
    r, t, columns = _build_report(["Cell"])

    request = rf.get("/")
    ctx = RequestContext(request, dict(request=request))

    render_context = django_tables2._report(r, ctx)
    Template(r.template).render(render_context)

    table_instance = render_context["elements"]["element"]["table"]

    column_instances = list(type(table_instance).base_columns.values())
    column_instances += list(table_instance.base_columns.values())
    # The columns actually used while rendering are the deep copies held by the
    # bound columns, so check those as well.
    column_instances += [bc.column for bc in table_instance.columns.iterall()]

    for column_instance in column_instances:
        pinned = [
            name
            for name, value in vars(column_instance).items()
            if isinstance(value, Template)
        ]
        assert pinned == []


@pytest.mark.django_db
def test_compiled_template_cache_is_used(rf):
    r, t, columns = _build_report(["Cell"], values=(1, 2, 3))

    request = rf.get("/")

    django_tables2.as_html(r, RequestContext(request, dict(request=request)))
    hits_after_first = django_tables2._compiled_template.cache_info().hits

    # Three rows, one column: the template is compiled once and reused.
    assert hits_after_first > 0

    django_tables2.as_html(r, RequestContext(request, dict(request=request)))
    assert django_tables2._compiled_template.cache_info().hits > hits_after_first


@pytest.mark.django_db
def test_concurrent_render(rf):
    r, t, columns = _build_report(
        ["Cell"], column_template="[{{ row_counter }}|{{ value }}]", values=(11, 22, 33)
    )

    request = rf.get("/")

    # The data is materialized and the table classes are built up front so the
    # threads only exercise the shared compiled-template path, without touching
    # the database from a connection that cannot see this test's transaction.
    object_list = list(MyTestFoo.objects.all().order_by("i"))
    tables = [django_tables2.table(t, request, object_list) for _ in range(2)]

    results = {}
    errors = []

    def render(index):
        try:
            results[index] = tables[index].as_html(request)
        except Exception as e:  # pragma: no cover - only on a real failure
            errors.append(e)

    threads = [threading.Thread(target=render, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(results) == 2
    assert "[0|11]" in results[0]
    assert results[0] == results[1]


@pytest.mark.django_db
def test_report(rf):
    baker.make(MyTestFoo, i=5)
    baker.make(MyTestFoo, i=5)

    r = baker.make(Report, title="Report title")

    t = baker.make(
        Table, label="tmp", base_model=ContentType.objects.get_for_model(MyTestFoo)
    )

    baker.make(
        Column,
        label="Value of i",
        parent=t,
        attr_name="i",
        position=0,
        display_totals=True,
    )

    baker.make(
        Column,
        label="also value of i",
        parent=t,
        attr_name="i",
        template="",
        position=1,
        display_totals=False,
    )

    ds = baker.make(
        Datasource,
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        dsl_query="i > 0 AND i < 10",
    )

    re = baker.make(
        ReportElement,
        title="Report element title",
        slug="report-element-title",
        table=t,
        parent=r,
        datasource=ds,
    )
    assert "title" in re.title

    r.set_base_queryset(MyTestFoo.objects.all())

    request = rf.get("/")
    args = r, RequestContext(request, dict(request=request))
    res = django_tables2.as_html(*args)

    assert res is not None

    bs = BeautifulSoup(res, "html.parser")  # html5lib") # lxml")
    assert len(bs.table.tbody.find_all("td")) == 4
    assert bs.table.tfoot.td.text == "10"

    # Run extra export procs
    django_tables2.as_tablib_databook(*args)
    django_tables2.as_tablib_dataset(*args)
    res = django_tables2.as_docx(*args)
    res.seek(0)
    assert len(res.read()) != 0


@pytest.mark.django_db
def test_catchall_except_catchall(rf):
    for a in range(1, 6):
        baker.make(MyTestFoo, i=a)

    mtf = ContentType.objects.get_for_model(MyTestFoo)

    r = baker.make(Report)
    t = baker.make(Table, base_model=mtf)
    baker.make(Column, parent=t)

    ds = baker.make(Datasource, base_model=mtf, dsl_query="i > 0 AND i < 3")
    re = baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )
    re.clean()

    ds = baker.make(Datasource, base_model=mtf, dsl_query="i > 3")
    re = baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )
    re.clean()

    rex = baker.make(
        ReportElement,
        table=t,
        parent=r,
        datasource=None,
        base_model=mtf,
        data_from=DATA_FROM_EXCEPT_CATCHALL,
    )
    rex.clean()

    r.set_base_queryset(MyTestFoo.objects.all())

    res = django_tables2._report(r, {"request": None})
    assert res["except_catchall"]["test_app_mytestfoo"].count() == 1
    assert res["except_catchall"]["test_app_mytestfoo"][0].i == 3


@pytest.mark.django_db
def test_sum_text_field(rf):
    for a in range(1, 6):
        baker.make(MyTestBar)

    mtb = ContentType.objects.get_for_model(MyTestBar)

    r = baker.make(Report)
    t = baker.make(Table, base_model=mtb)
    baker.make(Column, parent=t, display_totals=True)

    ds = baker.make(Datasource, base_model=mtb, dsl_query='i = "my test bar"')
    baker.make(
        ReportElement,
        table=t,
        parent=r,
        datasource=ds,
        data_from=DATA_FROM_DATASOURCE,
        slug="lol",
    )

    r.set_base_queryset(MyTestBar.objects.all())

    res = django_tables2._report(r, {"request": None})
    lol = res["elements"]["lol"]

    assert lol["table"].columns[0].has_footer()

    assert lol["table"].columns[0].footer == "5"


@pytest.mark.django_db
def test_catchall_except_catchall_djangoql(rf):
    for a in range(1, 6):
        baker.make(MyTestFoo, i=a)

    mtf = ContentType.objects.get_for_model(MyTestFoo)

    r = baker.make(Report)
    t = baker.make(Table, base_model=mtf)
    baker.make(Column, parent=t)

    ds = baker.make(
        Datasource, base_model=mtf, query_language="djangoql", dsl_query="i < 3"
    )
    baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )

    ds = baker.make(
        Datasource, base_model=mtf, query_language="djangoql", dsl_query="i > 3"
    )
    baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )

    baker.make(
        ReportElement,
        table=t,
        parent=r,
        datasource=None,
        base_model=mtf,
        data_from=DATA_FROM_EXCEPT_CATCHALL,
    )

    r.set_base_queryset(MyTestFoo.objects.all())

    res = django_tables2._report(r, {"request": None})
    assert res["except_catchall"]["test_app_mytestfoo"].count() == 1
    assert res["except_catchall"]["test_app_mytestfoo"][0].i == 3


@pytest.mark.django_db
def test_except_catchall_rendered_into_element_object_list(rf):
    # Regression: the except-catchall element must receive the filtered
    # queryset in render_context["elements"][slug]["object_list"]. The lookup
    # key has to be built from ContentType.model (e.g. "mytestfoo"), which
    # differs from ContentType.name ("my test foo") whenever a model's
    # verbose_name is not identical to its model name -- otherwise the lookup
    # misses and the rendered table is silently empty.
    for a in range(1, 6):
        baker.make(MyTestFoo, i=a)

    mtf = ContentType.objects.get_for_model(MyTestFoo)

    r = baker.make(Report)
    t = baker.make(Table, base_model=mtf)
    baker.make(Column, parent=t)

    ds = baker.make(
        Datasource, base_model=mtf, query_language="djangoql", dsl_query="i < 3"
    )
    baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )

    ds = baker.make(
        Datasource, base_model=mtf, query_language="djangoql", dsl_query="i > 3"
    )
    baker.make(
        ReportElement, table=t, parent=r, datasource=ds, data_from=DATA_FROM_DATASOURCE
    )

    ec_elem = baker.make(
        ReportElement,
        table=t,
        parent=r,
        datasource=None,
        base_model=mtf,
        data_from=DATA_FROM_EXCEPT_CATCHALL,
    )

    r.set_base_queryset(MyTestFoo.objects.all())

    res = django_tables2._report(r, {"request": None})

    object_list = res["elements"][ec_elem.slug]["object_list"]
    assert object_list.count() == 1
    assert object_list[0].i == 3
