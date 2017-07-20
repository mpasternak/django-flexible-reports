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
