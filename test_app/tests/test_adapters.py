# -*- encoding: utf-8 -*-
import pytest
from bs4 import BeautifulSoup
from django.contrib.contenttypes.models import ContentType
from django.template.context import RequestContext
from flexible_reports.adapters import django_tables2
from flexible_reports.models import Column, Datasource, Report, ReportElement, Table
from flexible_reports.models.report import DATA_FROM_DATASOURCE, DATA_FROM_EXCEPT_CATCHALL
from model_mommy import mommy
from test_app.models import MyTestBar

from ..models import MyTestFoo


@pytest.mark.django_db
def test_report(rf):
    mommy.make(MyTestFoo, i=5)
    mommy.make(MyTestFoo, i=5)

    r = mommy.make(Report,
                   title="Report title")

    t = mommy.make(Table,
                   label="tmp",
                   base_model=ContentType.objects.get_for_model(MyTestFoo))

    mommy.make(Column,
               label="Value of i",
               parent=t,
               attr_name="i",
               position=0,
               display_totals=True)

    mommy.make(Column,
               label="also value of i",
               parent=t,
               attr_name="i",
               template="",
               position=1,
               display_totals=False)

    ds = mommy.make(Datasource,
                    base_model=ContentType.objects.get_for_model(MyTestFoo),
                    dsl_query="i > 0 AND i < 10")

    re = mommy.make(ReportElement,
                    title="Report element title",
                    slug="report-element-title",
                    table=t,
                    parent=r,
                    datasource=ds)
    assert "title" in re.title

    r.set_base_queryset(MyTestFoo.objects.all())

    request = rf.get('/')
    args = r, RequestContext(request, dict(request=request))
    res = django_tables2.as_html(*args)

    assert res is not None

    bs = BeautifulSoup(res, "lxml")
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
        mommy.make(MyTestFoo, i=a)

    mtf = ContentType.objects.get_for_model(MyTestFoo)

    r = mommy.make(Report)
    t = mommy.make(Table, base_model=mtf)
    mommy.make(Column, parent=t)

    ds = mommy.make(Datasource, base_model=mtf, dsl_query="i > 0 AND i < 3")
    re = mommy.make(ReportElement, table=t, parent=r, datasource=ds,
                    data_from=DATA_FROM_DATASOURCE)
    re.clean()

    ds = mommy.make(Datasource, base_model=mtf, dsl_query="i > 3")
    re = mommy.make(ReportElement, table=t, parent=r, datasource=ds,
                    data_from=DATA_FROM_DATASOURCE)
    re.clean()

    rex = mommy.make(ReportElement,
                     table=t,
                     parent=r,
                     datasource=None,
                     base_model=mtf,
                     data_from=DATA_FROM_EXCEPT_CATCHALL)
    rex.clean()

    r.set_base_queryset(MyTestFoo.objects.all())

    res = django_tables2._report(r, {'request': None})
    assert res['except_catchall']['test_app_mytestfoo'].count() == 1
    assert res['except_catchall']['test_app_mytestfoo'][0].i == 3


@pytest.mark.django_db
def test_sum_text_field(rf):
    for a in range(1, 6):
        mommy.make(MyTestBar)

    mtb = ContentType.objects.get_for_model(MyTestBar)

    r = mommy.make(Report)
    t = mommy.make(Table, base_model=mtb)
    mommy.make(Column, parent=t, display_totals=True)

    ds = mommy.make(Datasource, base_model=mtb, dsl_query='i = "my test bar"')
    mommy.make(ReportElement, table=t, parent=r, datasource=ds,
               data_from=DATA_FROM_DATASOURCE,
               slug='lol')

    r.set_base_queryset(MyTestBar.objects.all())

    res = django_tables2._report(r, {'request': None})
    lol = res['elements']['lol']

    assert lol['table'].columns[0].has_footer()

    assert lol['table'].columns[0].footer == "5"
