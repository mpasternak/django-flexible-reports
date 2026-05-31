.. :changelog:

History
-------

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
