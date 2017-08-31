# -*- encoding: utf-8 -*-

from flexible_reports.adapters.util import strip_tags

def test_strip_tags():
    html = "<p>Good, <b>bad</b>, and <i>ug<b>l</b><u>y</u></i></p>"
    invalid_tags = ['b', 'i', 'u']
    assert strip_tags(html, invalid_tags) == "<p>Good, bad, and ugly</p>"
