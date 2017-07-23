# -*- encoding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

class WithBaseModel(models.Model):
    base_model = models.ForeignKey(
        ContentType,
        verbose_name=_("Base model"),
    )

    class Meta:
        abstract = True


class Labelled(models.Model):
    label = models.TextField()

    def __str__(self):
        return self.label

    class Meta:
        abstract = True


class Titled(models.Model):
    title = models.TextField()

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
        ordering = ('position',)
