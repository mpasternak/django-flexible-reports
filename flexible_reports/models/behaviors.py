# -*- encoding: utf-8 -*-

from django.db import models


class Labelled(models.Model):
    label = models.CharField(
        max_length=250
    )

    def __str__(self):
        return self.label


class Titled(models.Model):
    title = models.TextField(
        null=True,
        blank=True)
    subtitle = models.TextField(
        null=True,
        blank=True)

    def __str__(self):
        return self.title

    class Meta:
        abstract = True


class Orderable(models.Model):
    """Can be placed in an order. Has a position. This field name is the
    default for Grappelli. """
    position = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
