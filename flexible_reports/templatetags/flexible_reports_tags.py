# -*- encoding: utf-8 -*-
from django import template
from django.template.base import Template

register = template.Library()


@register.simple_tag(takes_context=True)
def flexible(context, report):
    return report.as_html(parent_context=context)


@register.simple_tag(takes_context=True)
def render(context, value):
    return Template(value).render(context)
