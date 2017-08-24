# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-23 23:52
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flexible_reports', '0004_auto_20170823_2342'),
    ]

    operations = [
        migrations.AddField(
            model_name='column',
            name='attrs',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='HTML attributes'),
        ),
    ]
