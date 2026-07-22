# -*- encoding: utf-8 -*-

"""Regression guard: the Clone button must survive grappelli.

``flexible_reports/templates/admin/flexible_reports/change_form_with_clone.html``
does ``{% extends "admin/change_form.html" %}`` and overrides the
``object-tools-items`` block. django-grappelli ships its *own*
``admin/change_form.html``, so the block could be renamed or dropped upstream
and our button would silently disappear. Nothing else in the suite would
notice, because everywhere else grappelli is absent.

grappelli is an **optional** test dependency: the stock suite has to pass
without it, hence the ``importorskip`` below.
"""

import pytest

grappelli = pytest.importorskip(
    "grappelli",
    reason=(
        "django-grappelli is not installed -- these tests guard the Clone "
        "button against grappelli's own admin/change_form.html. Install it "
        "with `uv pip install django-grappelli` (or run `uv run --with "
        "django-grappelli pytest`) to enable them."
    ),
)

from django.conf import settings  # noqa: E402
from django.contrib import admin  # noqa: E402
from django.contrib.contenttypes.models import ContentType  # noqa: E402
from django.test import override_settings  # noqa: E402
from django.urls import include, path, reverse  # noqa: E402
from model_bakery import baker  # noqa: E402

from flexible_reports.models import Report, Table  # noqa: E402
from test_app.models import MyTestFoo  # noqa: E402

# grappelli needs its own routes reachable -- its change_form.html reverses
# ``grp_related_lookup`` & friends for the related-object widgets. Rather than
# adding a second URLconf module we point ROOT_URLCONF at *this* module; any
# module exposing ``urlpatterns`` will do.
urlpatterns = [
    path("grappelli/", include("grappelli.urls")),
    path("admin/", admin.site.urls),
]

# ``grappelli`` has to precede ``django.contrib.admin``: both ship
# ``templates/admin/change_form.html`` and the app-directories loader returns
# the first match, in INSTALLED_APPS order.
GRAPPELLI_INSTALLED_APPS = ["grappelli", *settings.INSTALLED_APPS]


@pytest.fixture(autouse=True)
def grappelli_active():
    """Activate grappelli for the duration of a test.

    ``override_settings(INSTALLED_APPS=...)`` is enough *and* is the only
    approach that works here, because it does three things a plain
    ``settings.INSTALLED_APPS.insert()`` would not:

    * ``apps.set_installed_apps()`` repopulates the app registry in the new
      order (grappelli's ``AppConfig.ready()`` runs, its templatetag libraries
      become importable);
    * ``django.test.signals.update_installed_apps`` clears the
      ``get_app_template_dirs`` ``lru_cache`` -- otherwise the tuple of
      ``.../templates`` dirs stays frozen from process start and grappelli's
      directory is never searched;
    * ``django.test.signals.reset_template_engines`` throws away the built
      engines, so the app-dirs loader is rebuilt from the new dir list.

    Skipping any of those leaves the *vanilla* admin templates in place while
    the settings claim otherwise -- see ``assert_grappelli_rendered`` for the
    check that catches exactly that failure mode.
    """
    with override_settings(
        INSTALLED_APPS=GRAPPELLI_INSTALLED_APPS,
        ROOT_URLCONF=__name__,
    ):
        yield


def assert_grappelli_rendered(response):
    """Prove grappelli's templates -- not Django's -- produced this page.

    This is the load-bearing assertion of the whole module. "The Clone button
    is in the HTML" passes identically when grappelli is *not* active, and
    ``response.templates`` is no help either: both projects name their template
    ``admin/change_form.html``, so the name matches either way.

    grappelli prefixes essentially every class and id with ``grp-``; a Table
    change form yields several hundred occurrences under grappelli and exactly
    zero under the stock admin.
    """
    html = response.content.decode()
    grp_hits = html.count("grp-")
    assert grp_hits > 100, (
        "grappelli's templates did not win -- only %d 'grp-' occurrences in "
        "the rendered page. The stock admin change_form.html was used, so "
        "everything else this test asserts is vacuous." % grp_hits
    )

    # Belt and braces: the *file* that rendered must live inside grappelli.
    origins = [
        t.origin.name
        for t in response.templates
        if t.name == "admin/change_form.html" and t.origin is not None
    ]
    assert origins, "admin/change_form.html was not rendered at all"
    assert any("grappelli" in origin for origin in origins), (
        "admin/change_form.html was resolved to %r, not to grappelli's copy" % origins
    )


def _make(model_name):
    if model_name == "table":
        return baker.make(
            Table,
            label="My table",
            base_model=ContentType.objects.get_for_model(MyTestFoo),
        )
    return baker.make(Report, title="My report", slug="my-report")


@pytest.mark.django_db
@pytest.mark.parametrize("model_name", ["table", "report"])
def test_clone_button_visible_under_grappelli(admin_client, model_name):
    obj = _make(model_name)
    change_url = reverse("admin:flexible_reports_%s_change" % model_name, args=[obj.pk])
    clone_url = reverse("admin:flexible_reports_%s_clone" % model_name, args=[obj.pk])

    res = admin_client.get(change_url)
    assert res.status_code == 200

    assert_grappelli_rendered(res)

    html = res.content.decode()
    start = html.index('action="%s"' % clone_url)
    form = html[start : html.index("</form>", start)]
    # Cloning writes to the database, so it must be a POST with a CSRF token.
    assert "csrfmiddlewaretoken" in form
    assert ">Clone<" in form

    # {{ block.super }} has to keep grappelli's own tools. grappelli renders
    # the History link without the vanilla ``historylink`` class, so assert on
    # the URL instead of the class name.
    history_url = reverse(
        "admin:flexible_reports_%s_history" % model_name, args=[obj.pk]
    )
    assert 'href="%s"' % history_url in html


@pytest.mark.django_db
@pytest.mark.parametrize("model_name", ["table", "report"])
def test_clone_posts_and_clones_under_grappelli(admin_client, model_name):
    """The button is wired up, not just painted on."""
    model = Table if model_name == "table" else Report
    obj = _make(model_name)
    clone_url = reverse("admin:flexible_reports_%s_clone" % model_name, args=[obj.pk])

    res = admin_client.post(clone_url)
    assert res.status_code == 302

    clone = model.objects.exclude(pk=obj.pk).get()
    assert res["Location"] == reverse(
        "admin:flexible_reports_%s_change" % model_name, args=[clone.pk]
    )

    # ...and the clone's own change form still offers the button.
    res = admin_client.get(res["Location"])
    assert res.status_code == 200
    assert_grappelli_rendered(res)
    assert (
        'action="%s"'
        % reverse("admin:flexible_reports_%s_clone" % model_name, args=[clone.pk])
        in res.content.decode()
    )
