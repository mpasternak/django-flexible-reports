import json
import shutil
import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from djangoql.schema import DjangoQLSchema

from flexible_reports import query_backends
from flexible_reports.models.datasource import Datasource
from test_app.models import MyTestFoo, MyTestForeign

SCHEMA_URL = "admin:flexible_reports_datasource_query_editor_schema"
SUGGESTIONS_URL = "admin:flexible_reports_datasource_query_editor_suggestions"
FORMAT_URL = "admin:flexible_reports_datasource_query_editor_format"

EDITOR_JS = (
    Path(__file__).resolve().parents[3]
    / "flexible_reports/static/flexible_reports/js/query_editor.js"
)


def _ct(model):
    return ContentType.objects.get_for_model(model)


@pytest.fixture
def staff_client(client):
    """Staff, but with no permission on datasources."""
    user = get_user_model().objects.create_user("staff", password="x", is_staff=True)
    client.force_login(user)
    return client


# -- the form ---------------------------------------------------------------


@pytest.mark.django_db
def test_add_form_wires_up_the_editor(admin_client):
    res = admin_client.get(reverse("admin:flexible_reports_datasource_add"))
    html = res.rendered_content
    assert 'class="flexible-reports-query"' in html
    assert 'data-schema-url="%s"' % reverse(SCHEMA_URL) in html
    assert 'data-format-url="%s"' % reverse(FORMAT_URL) in html
    assert "flexible_reports/js/query_editor.js" in html
    assert "flexible_reports/css/query_editor.css" in html
    # djangoql is an installed app in the test project: its completion widget
    # and its JavaScript catalog are loaded, the catalog first.
    i18n = reverse("admin:flexible_reports_datasource_query_editor_i18n")
    assert html.index(i18n) < html.index("djangoql/js/completion.js")
    assert html.index("djangoql/js/completion.js") < html.index("query_editor.js")


@pytest.mark.django_db
def test_editor_degrades_without_the_djangoql_app(admin_client, settings):
    # djangoql only needs to be importable to run reports. Without it in
    # INSTALLED_APPS there is no widget to load, and nothing may point at it.
    settings.INSTALLED_APPS = [a for a in settings.INSTALLED_APPS if a != "djangoql"]
    res = admin_client.get(reverse("admin:flexible_reports_datasource_add"))
    html = res.rendered_content
    assert "flexible_reports/js/query_editor.js" in html
    assert "djangoql/js/completion.js" not in html


@pytest.mark.django_db
def test_change_form_still_saves(admin_client):
    ds = Datasource.objects.create(
        label="ds", base_model=_ct(MyTestFoo), dsl_query="i = 5"
    )
    res = admin_client.post(
        reverse("admin:flexible_reports_datasource_change", args=[ds.pk]),
        {
            "label": "ds",
            "base_model": _ct(MyTestFoo).pk,
            "query_language": "djangoql",
            "dsl_query": "i = 5\nor i = 6",
            "sample_context": "{}",
            "distinct": "on",
        },
    )
    assert res.status_code == 302
    ds.refresh_from_db()
    assert ds.query_language == "djangoql"
    assert ds.dsl_query.replace("\r\n", "\n") == "i = 5\nor i = 6"


# -- schema -----------------------------------------------------------------


@pytest.mark.django_db
def test_schema_describes_the_chosen_model(admin_client):
    ct = _ct(MyTestForeign)
    res = admin_client.get(reverse(SCHEMA_URL), {"base_model": ct.pk})
    assert res.status_code == 200
    data = res.json()

    # The document djangoql's completion widget expects...
    assert data["djangoql"]["current_model"] == "test_app.mytestforeign"
    assert "parent" in data["djangoql"]["models"]["test_app.mytestforeign"]
    assert "i" in data["djangoql"]["models"]["test_app.mytestfoo"]
    assert data["djangoql"]["suggestions_api_url"] == "%s?base_model=%s" % (
        reverse(SUGGESTIONS_URL),
        ct.pk,
    )
    # ...and the field names and shortcuts shown for django-dsl.
    assert data["dsl"]["fields"] == ["id", "parent"]
    assert data["dsl"]["shortcuts"] == {"i": "parent__i"}


@pytest.mark.django_db
def test_schema_follows_the_model(admin_client):
    foo = admin_client.get(reverse(SCHEMA_URL), {"base_model": _ct(MyTestFoo).pk})
    assert foo.json()["djangoql"]["current_model"] == "test_app.mytestfoo"
    assert "i" in foo.json()["dsl"]["fields"]


@pytest.mark.django_db
@pytest.mark.parametrize("value", [None, "", "abc", "999999"])
def test_schema_unknown_model_is_404(admin_client, value):
    params = {} if value is None else {"base_model": value}
    assert admin_client.get(reverse(SCHEMA_URL), params).status_code == 404


@pytest.mark.django_db
def test_schema_uses_the_schema_class_of_the_backend(admin_client, monkeypatch):
    # A project that registers its own DjangoQL backend (to expose a custom
    # schema) gets that schema in the editor as well -- completion must offer
    # exactly what validation accepts.
    class NarrowSchema(DjangoQLSchema):
        def get_fields(self, model):
            return ["id"]

    class NarrowBackend(query_backends.DjangoQLQueryBackend):
        schema_class = NarrowSchema

    monkeypatch.setitem(
        query_backends.BACKENDS, query_backends.DJANGOQL, NarrowBackend()
    )

    ct = _ct(MyTestFoo)
    data = admin_client.get(reverse(SCHEMA_URL), {"base_model": ct.pk}).json()
    assert list(data["djangoql"]["models"]["test_app.mytestfoo"]) == ["id"]

    # The same class decides what a query may reference.
    ds = Datasource(
        label="x", base_model=ct, query_language="djangoql", dsl_query="i = 5"
    )
    with pytest.raises(Exception) as excinfo:
        ds.full_clean()
    assert "dsl_query" in excinfo.value.message_dict
    ds.dsl_query = "id > 0"
    ds.full_clean()
    assert ds.filter_queryset(MyTestFoo.objects.all()).count() == 0


@pytest.mark.django_db
def test_schema_respects_the_allowed_models(admin_client, settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = ["test_app.MyTestFoo"]
    ok = admin_client.get(reverse(SCHEMA_URL), {"base_model": _ct(MyTestFoo).pk})
    assert ok.status_code == 200

    other = _ct(MyTestForeign)
    assert (
        admin_client.get(reverse(SCHEMA_URL), {"base_model": other.pk}).status_code
        == 403
    )
    assert (
        admin_client.get(
            reverse(SUGGESTIONS_URL), {"base_model": other.pk, "field": "id"}
        ).status_code
        == 403
    )

    # A model some datasource already uses stays available: its change form
    # has to keep working.
    Datasource.objects.create(label="old", base_model=other, dsl_query="i = 5")
    assert (
        admin_client.get(reverse(SCHEMA_URL), {"base_model": other.pk}).status_code
        == 200
    )


@pytest.mark.django_db
def test_editor_views_need_datasource_permission(staff_client, client):
    ct = _ct(MyTestFoo)
    assert staff_client.get(reverse(SCHEMA_URL), {"base_model": ct.pk}).status_code == (
        403
    )
    assert (
        staff_client.get(
            reverse(SUGGESTIONS_URL), {"base_model": ct.pk, "field": "i"}
        ).status_code
        == 403
    )
    assert staff_client.post(reverse(FORMAT_URL), {"q": "a = 1"}).status_code == 403

    client.logout()
    res = client.get(reverse(SCHEMA_URL), {"base_model": ct.pk})
    assert res.status_code == 302 and "login" in res["Location"]


# -- suggestions --------------------------------------------------------------


@pytest.mark.django_db
def test_suggestions_endpoint_answers_for_the_chosen_model(admin_client, monkeypatch):
    from test_app.models import MyTestBar

    # Out of the box djangoql only suggests values for fields with choices;
    # a schema opts a text field in.
    class SuggestingSchema(DjangoQLSchema):
        suggest_options = {MyTestBar: ["i"]}

    class SuggestingBackend(query_backends.DjangoQLQueryBackend):
        schema_class = SuggestingSchema

    monkeypatch.setitem(
        query_backends.BACKENDS, query_backends.DJANGOQL, SuggestingBackend()
    )

    MyTestBar.objects.create(i="alpha")
    MyTestBar.objects.create(i="beta")
    res = admin_client.get(
        reverse(SUGGESTIONS_URL),
        {"base_model": _ct(MyTestBar).pk, "field": "i", "search": "al"},
    )
    assert res.status_code == 200
    assert res.json()["items"] == ["alpha"]


# -- format -------------------------------------------------------------------


@pytest.mark.django_db
def test_format_endpoint(admin_client):
    res = admin_client.post(
        reverse(FORMAT_URL), {"q": "a = 1 and b = 2", "language": "djangoql"}
    )
    assert res.status_code == 200
    assert res.json() == {"formatted": "a = 1\nand b = 2"}

    # django-dsl is the default language, as on the model.
    res = admin_client.post(reverse(FORMAT_URL), {"q": "a = 1 AND b = 2"})
    assert res.json() == {"formatted": "a = 1\nAND b = 2"}


@pytest.mark.django_db
def test_format_endpoint_reports_what_it_cannot_format(admin_client):
    res = admin_client.post(reverse(FORMAT_URL), {"q": 'a = "open', "language": "dsl"})
    assert res.status_code == 400
    assert "error" in res.json()


@pytest.mark.django_db
def test_format_endpoint_is_post_only(admin_client):
    assert admin_client.get(reverse(FORMAT_URL), {"q": "a = 1"}).status_code == 405


# -- the tokenizer behind the colouring ---------------------------------------


def _tokenize(text, language):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = (
        "const e = require(process.argv[1]);"
        "process.stdout.write(JSON.stringify("
        "e.tokenize(process.argv[2], process.argv[3])"
        ".filter(t => t.type !== 'ws').map(t => [t.type, t.value])))"
    )
    out = subprocess.run(
        [node, "-e", script, str(EDITOR_JS), text, language],
        capture_output=True,
        text=True,
        check=True,
    )
    return [tuple(pair) for pair in json.loads(out.stdout)]


def test_tokenizer_djangoql():
    assert _tokenize('a.b >= 10 and not_x in ("p", None)', "djangoql") == [
        ("name", "a.b"),
        ("operator", ">="),
        ("number", "10"),
        ("logical", "and"),
        ("name", "not_x"),
        ("operator", "in"),
        ("paren", "("),
        ("string", '"p"'),
        ("comma", ","),
        ("constant", "None"),
        ("paren", ")"),
    ]


def test_tokenizer_dsl():
    assert _tokenize('a__b IN ["x"] AND NOT d >= 2020-01-31 OR e = NULL', "dsl") == [
        ("name", "a__b"),
        ("operator", "IN"),
        ("paren", "["),
        ("string", '"x"'),
        ("paren", "]"),
        ("logical", "AND"),
        ("logical", "NOT"),
        ("name", "d"),
        ("operator", ">="),
        ("number", "2020-01-31"),
        ("logical", "OR"),
        ("name", "e"),
        ("operator", "="),
        ("constant", "NULL"),
    ]


def test_tokenizer_keeps_template_tags_whole():
    # Braces are not query syntax; a tag must not dissolve into error tokens.
    assert _tokenize("a = {{ obj.pk }} {% if x %}", "djangoql") == [
        ("name", "a"),
        ("operator", "="),
        ("template", "{{ obj.pk }}"),
        ("template", "{% if x %}"),
    ]


def test_tokenizer_is_total():
    # Anything it does not know becomes one-character error tokens, and the
    # text always adds up to the input.
    tokens = _tokenize("a = 1 # $", "dsl")
    assert ("error", "#") in tokens and ("error", "$") in tokens
