from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "flexible_reports",
            "0011_alter_reportelement_options_alter_column_attrs_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="datasource",
            name="query_language",
            field=models.CharField(
                choices=[("dsl", "django-dsl"), ("djangoql", "DjangoQL")],
                default="dsl",
                max_length=16,
                verbose_name="Query language",
            ),
        ),
        migrations.AlterField(
            model_name="datasource",
            name="dsl_query",
            field=models.TextField(verbose_name="Query"),
        ),
    ]
