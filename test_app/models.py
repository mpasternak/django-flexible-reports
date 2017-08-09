# -*- encoding: utf-8 -*-

from django.db import models


class MyTestFoo(models.Model):
    i = models.IntegerField(default=5)


class MyTestForeign(models.Model):
    django_dsl_shortcuts = {
        'i': 'parent__i'
    }
    parent = models.ForeignKey(MyTestFoo)
