# -*- encoding: utf-8 -*-
from django import template
from django.template.base import Template

from ..adapters.django_tables2 import report as django_tables2_report

register = template.Library()


@register.simple_tag(takes_context=True)
def flexible(context, report):
    return django_tables2_report(report, parent_context=context)


@register.simple_tag(takes_context=True)
def render(context, value):
    return Template(value).render(context)
