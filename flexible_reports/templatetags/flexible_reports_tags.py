# -*- encoding: utf-8 -*-
from django import template
from django.template.base import Template

from ..adapters import django_tables2

register = template.Library()


@register.simple_tag(takes_context=True)
def flexible(context, report):
    return django_tables2.as_html(report, parent_context=context)


@register.simple_tag(takes_context=True)
def render(context, value):
    return Template(value).render(context)
