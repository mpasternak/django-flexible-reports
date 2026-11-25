from django.conf import settings
from django.db import migrations


def fill_missing_base_models(apps, schema_editor):
    """Give every table a ``base_model`` again before 0015 is reversed.

    Reversing 0015 restores NOT NULL on ``Table.base_model``, which the
    database refuses while tables created on 0.6 carry NULL there. The model
    is recovered from where the table is used -- the datasource of a report
    element, or the element's own model -- and, for a table used nowhere, from
    the first entry of ``FLEXIBLE_REPORTS_BASE_MODELS``.
    """
    Table = apps.get_model("flexible_reports", "Table")
    ReportElement = apps.get_model("flexible_reports", "ReportElement")
    ContentType = apps.get_model("contenttypes", "ContentType")

    default_id = None
    labels = getattr(settings, "FLEXIBLE_REPORTS_BASE_MODELS", None) or []
    if labels and not isinstance(labels, str):
        app_label, _, model_name = labels[0].partition(".")
        default = ContentType.objects.filter(
            app_label=app_label, model=model_name.lower()
        ).first()
        default_id = default.pk if default is not None else None

    unresolved = []
    for table in Table.objects.filter(base_model__isnull=True):
        content_type_id = None
        elements = ReportElement.objects.filter(table=table).order_by("pk")
        for element in elements.select_related("datasource"):
            if element.datasource_id is not None:
                content_type_id = element.datasource.base_model_id
            else:
                content_type_id = element.base_model_id
            if content_type_id is not None:
                break
        content_type_id = content_type_id or default_id
        if content_type_id is None:
            unresolved.append(table)
            continue
        table.base_model_id = content_type_id
        table.save(update_fields=["base_model"])

    if unresolved:
        raise RuntimeError(
            "Cannot reverse flexible_reports.0015: %d table(s) have no base "
            "model and none can be worked out (pk: %s). Set "
            "FLEXIBLE_REPORTS_BASE_MODELS, or put the tables into a report or "
            "delete them, and migrate again."
            % (len(unresolved), ", ".join(str(t.pk) for t in unresolved))
        )


class Migration(migrations.Migration):
    """No schema or data change going forward.

    It exists for its reverse step, which runs right before the reverse of
    0015 and makes that one possible -- see ``fill_missing_base_models``.
    """

    dependencies = [
        ("flexible_reports", "0015_table_base_model_optional"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, fill_missing_base_models),
    ]
