# -*- encoding: utf-8 -*-

import pytest
from django.template.base import Template
from django.template.context import RequestContext
from model_bakery import baker

from flexible_reports.models.report import Report
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_templatetags_flexible(rf):
    x = "{% load flexible_reports_tags %}{% flexible report %}"

    r = baker.make(Report)
    r.set_base_queryset(MyTestFoo.objects.all())

    request = rf.get("/")
    ctx = RequestContext(request, dict(request=request, report=r))

    Template(x).render(context=ctx)


@pytest.mark.django_db
def test_templatetags_render(rf):
    x = "{% load flexible_reports_tags %}{% render report %}"

    r = baker.make(Report, template="foobar")
    r.set_base_queryset(MyTestFoo.objects.all())

    request = rf.get("/")
    ctx = RequestContext(request, dict(request=request, report="foobar"))

    res = Template(x).render(context=ctx)
    assert res == "foobar"
