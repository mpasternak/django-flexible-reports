import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls.base import reverse
from model_bakery import baker

from flexible_reports.models.datasource import Datasource
from flexible_reports.models.report import Report, ReportElement
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_report(admin_client):
    r = baker.make(Report)
    ds = baker.make(
        Datasource,
        base_model=ContentType.objects.get_for_model(MyTestFoo),
        dsl_query="i=5",
    )
    baker.make(ReportElement, datasource=ds, parent=r)

    admin_client.get(reverse("admin:flexible_reports_report_changelist"))


@pytest.mark.django_db
def test_report_element_form_does_not_ask_for_a_model(admin_client):
    res = admin_client.get(reverse("admin:flexible_reports_report_add"))
    assert "reportelement_set" in res.rendered_content
    assert "base_model" not in res.rendered_content


def _report_change_data(report, **element_overrides):
    """POST data for the report change form, one dict entry per inline field."""
    elements = list(report.reportelement_set.order_by("position", "pk"))
    data = {
        "title": report.title,
        "slug": report.slug,
        "template": report.template,
        "reportelement_set-TOTAL_FORMS": len(elements),
        "reportelement_set-INITIAL_FORMS": len(elements),
        "reportelement_set-MIN_NUM_FORMS": 0,
        "reportelement_set-MAX_NUM_FORMS": 1000,
        "_save": "Save",
    }
    for index, element in enumerate(elements):
        prefix = "reportelement_set-%d-" % index
        values = {
            "id": element.pk,
            "parent": report.pk,
            "title": element.title,
            "slug": element.slug,
            "data_from": element.data_from,
            "datasource": element.datasource_id or "",
            "table": element.table_id,
            "position": element.position,
        }
        values.update(element_overrides)
        data.update({prefix + name: value for name, value in values.items()})
    return data


@pytest.mark.django_db
def test_catchall_with_stored_model_can_be_switched_to_a_datasource(admin_client):
    # Elements saved before 0.6 (and by code) carry a base_model the form no
    # longer shows. Pointing such an element at a datasource used to end in
    # ``ValueError: 'ReportElementForm' has no field named 'base_model'``.
    from flexible_reports.models.report import (
        DATA_FROM_DATASOURCE,
        DATA_FROM_EXCEPT_CATCHALL,
    )
    from flexible_reports.models.table import Table

    ct = ContentType.objects.get_for_model(MyTestFoo)
    report = Report.objects.create(title="r", slug="r", template="x")
    element = ReportElement.objects.create(
        parent=report,
        title="rest",
        slug="rest",
        data_from=DATA_FROM_EXCEPT_CATCHALL,
        base_model=ct,
        table=baker.make(Table, label="t", base_model=None),
    )
    ds = Datasource.objects.create(label="ds", base_model=ct, dsl_query="i = 5")

    res = admin_client.post(
        reverse("admin:flexible_reports_report_change", args=[report.pk]),
        _report_change_data(report, data_from=DATA_FROM_DATASOURCE, datasource=ds.pk),
    )

    assert res.status_code == 302, res.rendered_content
    element.refresh_from_db()
    assert element.datasource == ds
    assert element.base_model is None


@pytest.mark.django_db
def test_catchall_with_stored_model_survives_an_unrelated_edit(admin_client):
    # Saving the report without touching the element must not strip the model
    # an "except catchall" element stores.
    from flexible_reports.models.report import DATA_FROM_EXCEPT_CATCHALL
    from flexible_reports.models.table import Table

    ct = ContentType.objects.get_for_model(MyTestFoo)
    report = Report.objects.create(title="r", slug="r", template="x")
    element = ReportElement.objects.create(
        parent=report,
        title="rest",
        slug="rest",
        data_from=DATA_FROM_EXCEPT_CATCHALL,
        base_model=ct,
        table=baker.make(Table, label="t", base_model=None),
    )

    data = _report_change_data(report)
    data["title"] = "renamed"
    res = admin_client.post(
        reverse("admin:flexible_reports_report_change", args=[report.pk]), data
    )

    assert res.status_code == 302, res.rendered_content
    element.refresh_from_db()
    assert element.base_model == ct
