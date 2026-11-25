"""The short list of models offered as a "base model" in the admin.

``base_model`` is a foreign key to ``ContentType``, so without help the admin
offers every model of the project -- sessions, permissions, task queues and all.
``settings.FLEXIBLE_REPORTS_BASE_MODELS`` narrows that to the handful that make
sense as report sources::

    FLEXIBLE_REPORTS_BASE_MODELS = ["library.Book", "library.Author"]

The first entry is preselected on the "add datasource" form and the list is
shown in the order given. Leaving the setting out (or ``None``) keeps the
historical behaviour: every model is offered and nothing is preselected.

This is a filter on *admin forms* only. Rows that already point at a model
outside the list keep working, keep showing their model on the change form and
can be saved again; nothing here touches model validation or rendering.
"""

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Case, IntegerField, Q, When

SETTING_NAME = "FLEXIBLE_REPORTS_BASE_MODELS"


def get_allowed_models():
    """Model classes named by the setting, in order; ``None`` when it is unset."""
    labels = getattr(settings, SETTING_NAME, None)
    if labels is None:
        return None
    if isinstance(labels, str):
        raise ImproperlyConfigured(
            "%s must be a list of 'app_label.ModelName' strings, not a string."
            % SETTING_NAME
        )
    models = []
    for label in labels:
        try:
            models.append(apps.get_model(label))
        except (LookupError, ValueError) as e:
            raise ImproperlyConfigured(
                "%s: %r is not an installed model (%s)." % (SETTING_NAME, label, e)
            ) from e
    return models


def get_allowed_content_types():
    """``ContentType`` rows for :func:`get_allowed_models`; ``None`` when unset.

    ``for_concrete_model=False`` so that a proxy or an unmanaged model named in
    the setting maps to its own content type, the same one a datasource created
    for it would store.
    """
    models = get_allowed_models()
    if models is None:
        return None
    return [
        ContentType.objects.get_for_model(model, for_concrete_model=False)
        for model in models
    ]


def get_default_content_type():
    """The first allowed content type, or ``None`` when the setting is unset."""
    allowed = get_allowed_content_types()
    return allowed[0] if allowed else None


def is_allowed(content_type, extra_pks=()):
    """Whether the admin may expose ``content_type`` (e.g. to the query editor).

    ``extra_pks`` lets a caller admit content types that are already in use.
    """
    allowed = get_allowed_content_types()
    if allowed is None:
        return True
    return content_type.pk in {ct.pk for ct in allowed} | set(extra_pks)


def limit_base_model_field(field, keep_pks=(), set_initial=False):
    """Narrow a ``base_model`` form field to the allowed content types.

    ``keep_pks`` are content types the field must keep offering whatever the
    setting says -- the value the edited row already has. Without that an old
    datasource for a model that has since left the list could not be saved.
    """
    allowed = get_allowed_content_types()
    if allowed is None:
        return

    keep_pks = [pk for pk in keep_pks if pk is not None]
    allowed_pks = [ct.pk for ct in allowed]
    # Listed models first, in the order of the setting; the kept ones after.
    order = Case(
        *[When(pk=pk, then=position) for position, pk in enumerate(allowed_pks)],
        default=len(allowed_pks),
        output_field=IntegerField(),
    )
    field.queryset = ContentType.objects.filter(
        Q(pk__in=allowed_pks) | Q(pk__in=keep_pks)
    ).order_by(order, "app_label", "model")
    if set_initial and allowed_pks:
        field.initial = allowed_pks[0]
