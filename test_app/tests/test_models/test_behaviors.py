# -*- encoding: utf-8 -*-
from test_app.models import RealLabelled, RealTitled

VAL = "foo"


def test_labelled():
    x = RealLabelled()
    x.label = VAL

    assert str(x) == VAL


def test_titled():
    x = RealTitled()
    x.title = VAL
    assert str(x) == VAL
