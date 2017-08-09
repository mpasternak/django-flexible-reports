# -*- encoding: utf-8 -*-
from flexible_reports.models.behaviors import Labelled, Titled

VAL = "foo"


def test_labelled():
    x = Labelled()
    x.label = VAL

    assert str(x) == VAL


def test_titled():
    x = Titled()
    x.title = VAL
    assert str(x) == VAL
