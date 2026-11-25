from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.forms import Media
from django.http import Http404, JsonResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST
from django.views.i18n import JavaScriptCatalog

from .. import utils
from ..base_models import is_allowed, limit_base_model_field
from ..models.datasource import Datasource
from ..query_backends import DJANGOQL, DSL, get_backend
from ..query_format import QueryFormatError, format_query
from .helpers import SmallerTextarea

#: Marks the query textarea for ``flexible_reports/js/query_editor.js``.
QUERY_EDITOR_CLASS = "flexible-reports-query"


def _djangoql_installed():
    # djangoql's completion widget is shipped as that app's static files (and
    # its translations as its JavaScript catalog), which Django only serves for
    # an installed app. The Python package is always importable -- it is a hard
    # dependency -- so this is purely about the browser side.
    return apps.is_installed("djangoql")


class DatasourceForm(forms.ModelForm):
    # Validation lives on Datasource.clean(), which dispatches to the query
    # backend selected by ``query_language``; the ModelForm runs it for us.
    class Meta:
        model = Datasource
        fields = [
            "label",
            "base_model",
            "query_language",
            "dsl_query",
            "sample_context",
            "distinct",
        ]
        widgets = {
            "label": SmallerTextarea,
            "dsl_query": forms.Textarea(
                attrs={"cols": 75, "rows": 18, "class": QUERY_EDITOR_CLASS}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A subclass is free to leave the field out of its form.
        field = self.fields.get("base_model")
        if field is None:
            return
        adding = self.instance._state.adding
        limit_base_model_field(
            field, keep_pks=[self.instance.base_model_id], set_initial=adding
        )
        # ``field.initial`` alone is not enough: a ModelForm seeds
        # ``self.initial`` from the (empty) instance, and that ``None`` wins.
        if adding and field.initial and not self.initial.get("base_model"):
            self.initial["base_model"] = field.initial


@admin.register(Datasource)
class DatasourceAdmin(admin.ModelAdmin):
    list_display = ["label", "base_model", "query_language", "dsl_query_fmt"]
    form = DatasourceForm

    def dsl_query_fmt(self, obj):
        return format_html("<pre>{}</pre>", obj.dsl_query)

    dsl_query_fmt.short_description = _("Query")

    # -- query editor ------------------------------------------------------
    #
    # The query field is a plain <textarea> that query_editor.js upgrades in
    # the browser: syntax colouring, a Format button and, for DjangoQL, the
    # completion widget that ships with djangoql. Everything the script needs
    # from the server goes through the views below.

    def _url_name(self, suffix):
        return "%s_%s_%s" % (self.opts.app_label, self.opts.model_name, suffix)

    def _reverse(self, suffix):
        return reverse(
            "%s:%s" % (self.admin_site.name, self._url_name(suffix)),
            current_app=self.admin_site.name,
        )

    def get_urls(self):
        view = self.admin_site.admin_view
        urls = [
            path(
                "query-editor/schema/",
                view(require_GET(self.query_editor_schema)),
                name=self._url_name("query_editor_schema"),
            ),
            path(
                "query-editor/suggestions/",
                view(require_GET(self.query_editor_suggestions)),
                name=self._url_name("query_editor_suggestions"),
            ),
            path(
                "query-editor/format/",
                view(require_POST(self.query_editor_format)),
                name=self._url_name("query_editor_format"),
            ),
        ]
        if _djangoql_installed():
            urls.append(
                path(
                    "query-editor/i18n/",
                    view(
                        JavaScriptCatalog.as_view(packages=["djangoql"]),
                        cacheable=True,
                    ),
                    name=self._url_name("query_editor_i18n"),
                )
            )
        # Ahead of ModelAdmin's own routes, which end in a catch-all
        # ``<path:object_id>/`` that would swallow these.
        return urls + super().get_urls()

    @property
    def media(self):
        js = []
        css = ["flexible_reports/css/query_editor.css"]
        if _djangoql_installed():
            # The catalog first, so ``window.gettext`` knows djangoql's strings
            # by the time completion.js labels its operator hints.
            js += [self._reverse("query_editor_i18n"), "djangoql/js/completion.js"]
            css.insert(0, "djangoql/css/completion.css")
        js.append("flexible_reports/js/query_editor.js")
        return super().media + Media(css={"all": css}, js=js)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "dsl_query" and field is not None:
            field.widget.attrs.update(
                {
                    "data-schema-url": self._reverse("query_editor_schema"),
                    "data-format-url": self._reverse("query_editor_format"),
                    "data-label-format": _("Format"),
                    "data-label-fields": _("Available fields"),
                    "data-label-shortcuts": _("Shortcuts"),
                    "data-label-format-failed": _("The query could not be formatted"),
                    "spellcheck": "false",
                }
            )
        return field

    def _check_query_editor_permission(self, request):
        # The editor is part of the add and change forms, nothing more.
        if not (
            self.has_view_or_change_permission(request)
            or self.has_add_permission(request)
        ):
            raise PermissionDenied

    def _query_editor_model(self, request):
        """The model class named by ``?base_model=<content type pk>``."""
        self._check_query_editor_permission(request)
        try:
            content_type = ContentType.objects.get(pk=int(request.GET["base_model"]))
        except (KeyError, ValueError, ContentType.DoesNotExist):
            raise Http404("Unknown base model") from None
        model = content_type.model_class()
        if model is None:
            raise Http404("The base model is no longer installed")
        # With FLEXIBLE_REPORTS_BASE_MODELS set, the schema of a model is only
        # handed out for the listed models and for those already in use -- the
        # same set the form itself offers.
        in_use = Datasource.objects.values_list("base_model_id", flat=True)
        if not is_allowed(content_type, extra_pks=in_use.distinct()):
            raise PermissionDenied
        return model

    def query_editor_schema(self, request):
        """What the editor needs to know about one base model.

        ``djangoql`` is the introspection document of djangoql's completion
        widget; ``dsl`` lists the field names and the django-dsl shortcuts.
        """
        from djangoql.serializers import SuggestionsAPISerializer

        model = self._query_editor_model(request)
        schema = get_backend(DJANGOQL).get_schema_class()(model)
        suggestions_url = "%s?base_model=%s" % (
            self._reverse("query_editor_suggestions"),
            int(request.GET["base_model"]),
        )
        return JsonResponse(
            {
                "djangoql": SuggestionsAPISerializer(suggestions_url).serialize(schema),
                "dsl": {
                    "fields": sorted(f.name for f in model._meta.get_fields()),
                    "shortcuts": dict(utils.get_shortcuts(model)),
                },
            }
        )

    def query_editor_suggestions(self, request):
        """Value suggestions for one DjangoQL field (asked for by completion.js)."""
        from djangoql.views import SuggestionsAPIView

        model = self._query_editor_model(request)
        schema = get_backend(DJANGOQL).get_schema_class()(model)
        return SuggestionsAPIView.as_view(schema=schema)(request)

    def query_editor_format(self, request):
        """Re-indent the posted query (``q``, ``language``) for the Format button."""
        self._check_query_editor_permission(request)
        language = request.POST.get("language") or DSL
        try:
            formatted = format_query(request.POST.get("q", ""), language)
        except QueryFormatError as e:
            return JsonResponse({"error": str(e)}, status=400)
        return JsonResponse({"formatted": formatted})
