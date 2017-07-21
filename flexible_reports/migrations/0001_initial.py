# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-07-21 12:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django_dsl.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Labelled',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=250)),
            ],
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, null=True)),
                ('subtitle', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Report',
                'verbose_name_plural': 'Reports',
            },
        ),
        migrations.CreateModel(
            name='ReportElement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField(default=0)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flexible_reports.Report')),
            ],
        ),
        migrations.CreateModel(
            name='Table',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, null=True)),
                ('subtitle', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Table',
                'verbose_name_plural': 'Tables',
            },
        ),
        migrations.CreateModel(
            name='Column',
            fields=[
                ('labelled_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='flexible_reports.Labelled')),
                ('position', models.PositiveIntegerField(default=0)),
                ('sortable', models.BooleanField(default=True)),
                ('template', models.TextField(default='{{ obj.attribute }}')),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flexible_reports.Table')),
            ],
            options={
                'verbose_name': 'Column',
                'verbose_name_plural': 'Columns',
            },
            bases=('flexible_reports.labelled', models.Model),
        ),
        migrations.CreateModel(
            name='Datasource',
            fields=[
                ('labelled_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='flexible_reports.Labelled')),
                ('dsl_query', django_dsl.fields.DjangoDSLField(verbose_name='DSL query')),
                ('base_model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType', verbose_name='Base model')),
            ],
            options={
                'verbose_name': 'Datasource',
                'verbose_name_plural': 'Datasources',
            },
            bases=('flexible_reports.labelled',),
        ),
        migrations.AddField(
            model_name='reportelement',
            name='table',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flexible_reports.Table'),
        ),
        migrations.AddField(
            model_name='reportelement',
            name='datasource',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flexible_reports.Datasource'),
        ),
        migrations.AlterUniqueTogether(
            name='reportelement',
            unique_together=set([('parent', 'position')]),
        ),
        migrations.AlterUniqueTogether(
            name='column',
            unique_together=set([('parent', 'position')]),
        ),
    ]
