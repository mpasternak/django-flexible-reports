.. :changelog:

History
-------

0.3.1 (2026-05-31)
++++++++++++++++++

* ``Datasource`` gained an optional ``sample_context`` field holding example
  values for a query's template parameters, used to validate a parametrised
  query on save (both ``dsl`` and ``DjangoQL`` backends). It is nullable and
  must be a JSON object.
* Fix an admin 500 when clearing *Sample parameters* — the ``sample_context``
  JSONField is now nullable.
* Don't HTML-escape query parameters when rendering ``DjangoQL`` queries, so
  values containing ``<``, ``&`` or ``"`` are no longer corrupted. The
  ``django-dsl`` backend received the same fix in django-dsl 0.1.14.
* Fix the except-catchall element lookup (key off ``ContentType.model``) so the
  "everything except" table renders its rows instead of being silently empty;
  the caught querysets are OR-ed into a single exclude.
* Escape the datasource query shown in the admin changelist.
* Chain ``ValidationError`` from the original backend error for clearer
  diagnostics.

0.3.0 (2026-05-31)
++++++++++++++++++

* ``Datasource`` gained a ``query_language`` field and can now interpret its
  query with either ``django-dsl`` (default) or `DjangoQL`_. Query backends are
  pluggable (``flexible_reports.query_backends``). The django_tables2 adapter
  now consumes a filtered queryset from each datasource instead of a raw ``Q``
  object. Existing datasources keep working unchanged (default ``dsl``).

.. _DjangoQL: https://github.com/ivelum/djangoql

0.2.12 (2026-04-19)
+++++++++++++++++++

* Fix ``DeprecationWarning: Pickle, copy, and deepcopy support will be
  removed from itertools in Python 3.14`` raised when instantiating a
  ``Table`` with columns using ``CounterMixin``. The mixin now keeps
  the counter as a plain ``int`` instead of ``itertools.count`` so
  that columns stored in ``Table.base_columns`` remain deep-copyable
  on Python 3.14.
* ``tests.settings.DATABASES['default']['PORT']`` now respects the
  ``POSTGRES_PORT`` environment variable (default: ``5432``).

0.2.10 (2022-07-07)
+++++++++++++++++++

* Drop support for Django 2.2 and below,
* Drop support for Python 3.7,
* Python 3.10 support,
* Django 3.2 support,
* enable GitHub Actions,
* remove Travis-CI config.

0.1.0 (2017-07-20)
++++++++++++++++++

* First release on PyPI.
