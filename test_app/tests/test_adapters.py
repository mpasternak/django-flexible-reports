# -*- encoding: utf-8 -*-
import pytest
from bs4 import BeautifulSoup
from django.contrib.contenttypes.models import ContentType
from django.template.context import RequestContext
from model_mommy import mommy

from flexible_reports.adapters import django_tables2
from flexible_reports.models import Report, Table, ReportElement, Column, \
    Datasource
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

    c = mommy.make(Column,
                   label="Value of i",
                   parent=t,
                   attr_name="i",
                   position=0,
                   display_totals=True)

    c = mommy.make(Column,
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

    assert res != None

    bs = BeautifulSoup(res, "lxml")
    assert len(bs.table.tbody.find_all("td")) == 4
    assert bs.table.tfoot.td.text == "10"

    # Run extra export procs
    django_tables2.as_tablib_databook(*args)
    django_tables2.as_tablib_dataset(*args)    
    res = django_tables2.as_docx(*args)
    res.seek(0)
    assert len(res.read()) != 0
