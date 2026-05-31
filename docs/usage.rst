=====
Usage
=====

To use Django Flexible Reports in a project, add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'flexible_reports.apps.FlexibleReportsConfig',
        ...
    )

Add Django Flexible Reports's URL patterns:

.. code-block:: python

    from flexible_reports import urls as flexible_reports_urls


    urlpatterns = [
        ...
        url(r'^', include(flexible_reports_urls)),
        ...
    ]

Query languages
---------------

A ``Datasource`` interprets its query according to the ``query_language``
field:

* ``dsl`` (default) — `django-dsl`_ expressions, e.g.
  ``i > 0 AND i < 10``.
* ``djangoql`` — `DjangoQL`_ expressions, e.g. ``i > 0 and i < 10``.

In both cases the query is first rendered as a Django template, so it can be
parametrised from the report context, e.g. ``i = {{ value|default:0 }}``. Use a
``|default:`` filter so the query still validates when it is saved with an empty
context.

Existing datasources are unaffected: the column added by the migration defaults
to ``dsl``.

.. _django-dsl: https://pypi.org/project/django-dsl/
.. _DjangoQL: https://github.com/ivelum/djangoql
