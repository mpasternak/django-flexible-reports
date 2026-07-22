import pytest
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import resolve, reverse
from model_bakery import baker

from flexible_reports.models import Report, Table
from test_app.models import MyTestFoo


def _table():
    return baker.make(
        Table,
        label="My table",
        base_model=ContentType.objects.get_for_model(MyTestFoo),
    )


def _staff_user(django_user_model, model, codenames):
    """A staff user holding exactly ``codenames`` on ``model``."""
    user = django_user_model.objects.create_user(
        username="staff", password="secret", is_staff=True
    )
    content_type = ContentType.objects.get_for_model(model)
    user.user_permissions.set(
        Permission.objects.filter(content_type=content_type, codename__in=codenames)
    )
    return user


@pytest.mark.django_db
@pytest.mark.parametrize("model_name", ["table", "report"])
def test_clone_button_visible(admin_client, model_name):
    if model_name == "table":
        obj = _table()
    else:
        obj = baker.make(Report, title="My report", slug="my-report")

    change_url = reverse("admin:flexible_reports_%s_change" % model_name, args=[obj.pk])
    clone_url = reverse("admin:flexible_reports_%s_clone" % model_name, args=[obj.pk])

    res = admin_client.get(change_url)
    assert res.status_code == 200

    content = res.rendered_content
    start = content.index('action="%s"' % clone_url)
    form = content[start : content.index("</form>", start)]
    # The button posts -- a plain link would let a foreign page create objects
    # through an <img src="...">.
    assert "csrfmiddlewaretoken" in form
    # {{ block.super }} keeps the stock tools (History, View on site).
    assert "historylink" in content


@pytest.mark.django_db
def test_clone_url_not_swallowed_by_catchall(admin_client):
    # Regression guard: ModelAdmin.get_urls() ends with a backwards-compat
    # catch-all ``<path:object_id>/`` whose converter matches slashes. If our
    # route were appended *after* super().get_urls(), ``<pk>/clone/`` would
    # resolve to that RedirectView instead of our view.
    obj = _table()
    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])

    assert resolve(url).func.__name__ == "clone_view"

    res = admin_client.post(url)
    assert res.status_code == 302
    assert "/clone/change/" not in res["Location"]
    assert Table.objects.count() == 2


@pytest.mark.django_db
def test_clone_requires_post(admin_client):
    obj = _table()
    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])

    res = admin_client.get(url)
    assert res.status_code == 405
    assert Table.objects.count() == 1


@pytest.mark.django_db
def test_clone_anonymous_redirects_to_login(client):
    # admin_view has to wrap require_POST, not the other way round: an
    # anonymous GET must be sent to the login page instead of being told 405,
    # which would leak the existence of the URL.
    obj = _table()
    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])

    res = client.get(url)
    assert res.status_code == 302
    assert "/admin/login/" in res["Location"]


@pytest.mark.django_db
def test_clone_requires_add_permission(client, django_user_model):
    obj = _table()
    _staff_user(django_user_model, Table, ["view_table", "change_table"])
    client.login(username="staff", password="secret")

    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])
    res = client.post(url)
    assert res.status_code == 403
    assert Table.objects.count() == 1


@pytest.mark.django_db
def test_clone_requires_view_permission(client, django_user_model):
    obj = _table()
    _staff_user(django_user_model, Table, ["add_table"])
    client.login(username="staff", password="secret")

    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])
    res = client.post(url)
    assert res.status_code == 403
    assert Table.objects.count() == 1


@pytest.mark.django_db
def test_clone_missing_object_404(admin_client):
    url = reverse("admin:flexible_reports_table_clone", args=[123456])
    res = admin_client.post(url)
    assert res.status_code == 404


@pytest.mark.django_db
def test_clone_redirects_to_clone(admin_client):
    obj = _table()
    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])

    res = admin_client.post(url)
    assert res.status_code == 302

    clone = Table.objects.exclude(pk=obj.pk).get()
    assert res["Location"] == reverse(
        "admin:flexible_reports_table_change", args=[clone.pk]
    )


@pytest.mark.django_db
def test_clone_redirects_to_changelist_without_change_permission(
    client, django_user_model
):
    # Landing on the clone's change form would be a 403 for this user, so we
    # fall back to the changelist -- mirrors ModelAdmin._response_post_save.
    obj = _table()
    _staff_user(django_user_model, Table, ["add_table", "view_table"])
    client.login(username="staff", password="secret")

    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])
    res = client.post(url)
    assert res.status_code == 302
    assert res["Location"] == reverse("admin:flexible_reports_table_changelist")
    assert Table.objects.count() == 2


@pytest.mark.django_db
def test_clone_logs_addition(admin_client):
    obj = _table()
    url = reverse("admin:flexible_reports_table_clone", args=[obj.pk])

    admin_client.post(url)

    clone = Table.objects.exclude(pk=obj.pk).get()
    entry = LogEntry.objects.get(
        content_type=ContentType.objects.get_for_model(Table),
        object_id=str(clone.pk),
        action_flag=ADDITION,
    )
    # The message structure matters: it is what makes the history page say
    # "Added." instead of showing a raw string.
    assert entry.get_change_message() == "Added."
