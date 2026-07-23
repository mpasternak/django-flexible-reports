"""Pluggable query backends for :class:`~flexible_reports.models.datasource.Datasource`.

Each backend knows how to:

* turn the textual query stored on a datasource into a *filtered queryset*
  (``filter_queryset``), and
* validate that query at save time (``validate``).

The query string is always rendered as a Django template first, so reports can
parametrise queries with values from the report context.
"""

from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _

from . import utils

DSL = "dsl"
DJANGOQL = "djangoql"

QUERY_LANGUAGE_CHOICES = [
    (DSL, "django-dsl"),
    (DJANGOQL, "DjangoQL"),
]


def _check_not_empty(query):
    if not query or not query.strip():
        raise ValidationError(
            {"dsl_query": [ValidationError(_("Query must not be an empty string"))]}
        )


class DSLQueryBackend:
    """``django-dsl`` backend (the historical default)."""

    name = DSL

    def get_filter(self, query, model, context=None):
        """Return a ``Q`` object for ``query`` (django-dsl renders templates itself)."""
        from django_dsl import compiler

        return compiler.compile(
            query, shortcuts=utils.get_shortcuts(model), context=context or {}
        )

    def filter_queryset(self, base_queryset, query, context=None):
        return base_queryset.filter(
            self.get_filter(query, base_queryset.model, context)
        )

    def validate(self, query, model, context=None):
        """Validate ``query`` against ``model``.

        ``context`` supplies example values for any template parameters in the
        query, so a parametrised query can be validated against realistic
        values. Raises ``ValidationError`` on a compilation error or when a
        trial database query fails.
        """
        from django_dsl import compiler, exceptions

        _check_not_empty(query)
        try:
            compiled = compiler.compile(
                query, shortcuts=utils.get_shortcuts(model), context=context or {}
            )
        except exceptions.CompileException as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _("DSL compilation failed (%(error)s)"),
                            params={"error": e},
                        )
                    ]
                }
            ) from e
        try:
            model.objects.filter(compiled).first()
        except Exception as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _(
                                "An error occured while trying to run the actual "
                                "database query (%(error)s)"
                            ),
                            params={"error": e},
                        )
                    ]
                }
            ) from e


class DjangoQLQueryBackend:
    """`DjangoQL <https://github.com/ivelum/djangoql>`_ backend."""

    name = DJANGOQL

    def _render(self, query, context):
        # autoescape=False: parameter values feed a query language, not HTML.
        # Escaping would turn query-significant characters (``<``, ``&``, ``"``)
        # into entities and corrupt the query.
        return Template(query).render(Context(context or {}, autoescape=False))

    def get_filter(self, query, model, context=None):
        raise NotImplementedError(
            "The DjangoQL backend produces a filtered queryset, not a Q object; "
            "use filter_queryset() instead of get_filter()."
        )

    def filter_queryset(self, base_queryset, query, context=None):
        from djangoql.queryset import apply_search

        return apply_search(base_queryset, self._render(query, context))

    def validate(self, query, model, context=None):
        """Validate ``query`` against ``model``.

        ``context`` supplies example values for any template parameters in the
        query, so a parametrised query can be validated against realistic
        values. Raises ``ValidationError`` on a parser/schema error (e.g.
        unknown field) or when a trial database query fails.
        """
        from djangoql.exceptions import DjangoQLError
        from djangoql.queryset import apply_search

        _check_not_empty(query)
        rendered = self._render(query, context)
        try:
            apply_search(model.objects.all(), rendered).first()
        except DjangoQLError as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _("DjangoQL query is invalid (%(error)s)"),
                            params={"error": e},
                        )
                    ]
                }
            ) from e
        except Exception as e:
            raise ValidationError(
                {
                    "dsl_query": [
                        ValidationError(
                            _(
                                "An error occured while trying to run the actual "
                                "database query (%(error)s)"
                            ),
                            params={"error": e},
                        )
                    ]
                }
            ) from e


BACKENDS = {
    DSL: DSLQueryBackend(),
    DJANGOQL: DjangoQLQueryBackend(),
}


def get_backend(name):
    try:
        return BACKENDS[name]
    except KeyError:
        raise ValueError(
            "Unknown query backend %r. Available: %s" % (name, sorted(BACKENDS))
        ) from None
