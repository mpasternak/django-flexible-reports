import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls.base import reverse
from model_bakery import baker

from flexible_reports.models.table import SortIndividually, SortInGroup, Table
from test_app.models import MyTestFoo


@pytest.mark.django_db
def test_table(admin_client):
    PREFIX = "this is my prefix"

    t = baker.make(
        Table,
        sort_option=SortInGroup.id,
        group_prefix=PREFIX,
        base_model=ContentType.objects.get_for_model(MyTestFoo),
    )

    res = admin_client.get(reverse("admin:flexible_reports_table_changelist"))
    assert PREFIX in res.rendered_content

    t.sort_option = SortIndividually.id
    t.save()
    res = admin_client.get(reverse("admin:flexible_reports_table_changelist"))
    assert PREFIX not in res.rendered_content


@pytest.mark.django_db
def test_table_form_does_not_ask_for_a_model(admin_client):
    # The model belongs to the datasource; the table form no longer repeats it.
    res = admin_client.get(reverse("admin:flexible_reports_table_add"))
    assert "id_base_model" not in res.rendered_content


@pytest.mark.django_db
def test_table_can_be_added_without_a_model(admin_client):
    data = {
        "label": "new table",
        "sort_option": SortIndividually.id,
        "group_prefix": "",
        "attrs": "null",
        "empty_template": "nothing",
        "_save": "Save",
    }
    for prefix in ("column_set", "columnorder_set"):
        data.update(
            {
                prefix + "-TOTAL_FORMS": 0,
                prefix + "-INITIAL_FORMS": 0,
                prefix + "-MIN_NUM_FORMS": 0,
                prefix + "-MAX_NUM_FORMS": 1000,
            }
        )
    res = admin_client.post(reverse("admin:flexible_reports_table_add"), data)
    assert res.status_code == 302, res.rendered_content
    assert Table.objects.get(label="new table").base_model is None


@pytest.mark.django_db
def test_table_saved_with_a_model_keeps_it(admin_client):
    # Editing an old table through the new form must not wipe its stored model.
    ct = ContentType.objects.get_for_model(MyTestFoo)
    t = baker.make(Table, label="old", base_model=ct, sort_option=SortIndividually.id)
    data = {
        "label": "old, renamed",
        "sort_option": SortIndividually.id,
        "group_prefix": "",
        "attrs": "null",
        "empty_template": "nothing",
        "_save": "Save",
    }
    for prefix in ("column_set", "columnorder_set"):
        data.update(
            {
                prefix + "-TOTAL_FORMS": 0,
                prefix + "-INITIAL_FORMS": 0,
                prefix + "-MIN_NUM_FORMS": 0,
                prefix + "-MAX_NUM_FORMS": 1000,
            }
        )
    res = admin_client.post(
        reverse("admin:flexible_reports_table_change", args=[t.pk]), data
    )
    assert res.status_code == 302, res.rendered_content
    t.refresh_from_db()
    assert t.label == "old, renamed"
    assert t.base_model == ct


@pytest.mark.django_db
def test_table_changelist_shows_the_derived_model(admin_client):
    baker.make(
        Table,
        sort_option=SortIndividually.id,
        base_model=ContentType.objects.get_for_model(MyTestFoo),
    )
    res = admin_client.get(reverse("admin:flexible_reports_table_changelist"))
    assert "my test foo" in res.rendered_content
