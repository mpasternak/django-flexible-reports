# -*- encoding: utf-8 -*-

from django.db import models

from flexible_reports.models import Labelled, Titled


class RealLabelled(Labelled):
    pass


class RealTitled(Titled):
    pass


class MyTestFoo(models.Model):
    i = models.IntegerField(default=5)


class MyTestBar(models.Model):
    i = models.TextField(default="my test bar")


class MyTestForeign(models.Model):
    django_dsl_shortcuts = {"i": "parent__i"}
    parent = models.ForeignKey(MyTestFoo, on_delete=models.CASCADE)
