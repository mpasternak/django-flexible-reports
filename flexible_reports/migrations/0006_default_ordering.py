# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-30 23:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flexible_reports', '0005_column_attrs'),
    ]

    operations = [
        migrations.CreateModel(
            name='ColumnOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField(default=0, verbose_name='Position')),
                ('column', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flexible_reports.Column', verbose_name='Column')),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flexible_reports.Table', verbose_name='Table')),
            ],
            options={
                'ordering': ('position',),
                'abstract': False,
            },
        ),
    ]