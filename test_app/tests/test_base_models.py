import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured

from flexible_reports import base_models
from flexible_reports.admin.datasource import DatasourceForm
from flexible_reports.models.datasource import Datasource
from test_app.models import MyTestBar, MyTestFoo, MyTestForeign

SHORT_LIST = ["test_app.MyTestBar", "test_app.MyTestFoo"]


def _ct(model):
    return ContentType.objects.get_for_model(model)


def _choices(form):
    return [ct for ct in form.fields["base_model"].queryset]


@pytest.mark.django_db
def test_setting_unset_offers_every_model(settings):
    # The historical behaviour, and the default: nothing is filtered and
    # nothing is preselected.
    assert not hasattr(settings, "FLEXIBLE_REPORTS_BASE_MODELS")
    form = DatasourceForm()
    assert len(_choices(form)) == ContentType.objects.count()
    assert form["base_model"].initial is None
    assert base_models.get_allowed_models() is None
    assert base_models.is_allowed(_ct(MyTestForeign))


@pytest.mark.django_db
def test_setting_limits_and_orders_the_list(settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = SHORT_LIST
    form = DatasourceForm()
    # In the order of the setting, not alphabetically.
    assert _choices(form) == [_ct(MyTestBar), _ct(MyTestFoo)]


@pytest.mark.django_db
def test_first_model_is_preselected_on_the_add_form(settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = SHORT_LIST
    form = DatasourceForm()
    assert form["base_model"].initial == _ct(MyTestBar).pk
    assert 'value="%s" selected' % _ct(MyTestBar).pk in str(form["base_model"])


@pytest.mark.django_db
def test_explicit_initial_wins_over_the_default(settings):
    # e.g. the admin's ``?base_model=<pk>`` prefill.
    settings.FLEXIBLE_REPORTS_BASE_MODELS = SHORT_LIST
    form = DatasourceForm(initial={"base_model": _ct(MyTestFoo).pk})
    assert form["base_model"].initial == _ct(MyTestFoo).pk


@pytest.mark.django_db
def test_existing_datasource_keeps_a_model_outside_the_list(settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = SHORT_LIST
    foreign = _ct(MyTestForeign)
    ds = Datasource.objects.create(label="old", base_model=foreign, dsl_query="i = 5")

    form = DatasourceForm(instance=ds)
    # Its own model is still on offer (after the listed ones) and selected.
    assert _choices(form) == [_ct(MyTestBar), _ct(MyTestFoo), foreign]
    assert form["base_model"].initial == foreign.pk

    # ...and the datasource can be saved again without touching the model.
    form = DatasourceForm(
        instance=ds,
        data={
            "label": "old, renamed",
            "base_model": foreign.pk,
            "query_language": "dsl",
            "dsl_query": "i = 5",
            "distinct": True,
        },
    )
    assert form.is_valid(), form.errors
    assert form.save().base_model == foreign


@pytest.mark.django_db
def test_new_datasource_cannot_pick_a_model_outside_the_list(settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = SHORT_LIST
    form = DatasourceForm(
        data={
            "label": "new",
            "base_model": _ct(MyTestForeign).pk,
            "query_language": "dsl",
            "dsl_query": "i = 5",
            "distinct": True,
        }
    )
    assert not form.is_valid()
    assert "base_model" in form.errors


@pytest.mark.django_db
def test_setting_does_not_restrict_the_model_layer(settings):
    # The filter is an admin-form convenience. Code that builds reports, and
    # reports that already exist, are not affected by it.
    settings.FLEXIBLE_REPORTS_BASE_MODELS = SHORT_LIST
    for value in range(3):
        MyTestFoo.objects.create(i=value)
    ds = Datasource(
        label="x",
        base_model=_ct(MyTestForeign),
        dsl_query="parent__i = 5",
    )
    ds.full_clean()
    ds.save()
    assert ds.filter_queryset(MyTestForeign.objects.all()).count() == 0


@pytest.mark.django_db
def test_is_allowed(settings):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = SHORT_LIST
    assert base_models.is_allowed(_ct(MyTestFoo))
    assert not base_models.is_allowed(_ct(MyTestForeign))
    assert base_models.is_allowed(_ct(MyTestForeign), extra_pks=[_ct(MyTestForeign).pk])
    assert base_models.get_default_content_type() == _ct(MyTestBar)


@pytest.mark.parametrize("value", ["test_app.MyTestFoo", ["test_app.NoSuchModel"]])
def test_misconfigured_setting_is_reported(settings, value):
    settings.FLEXIBLE_REPORTS_BASE_MODELS = value
    with pytest.raises(ImproperlyConfigured):
        base_models.get_allowed_models()
