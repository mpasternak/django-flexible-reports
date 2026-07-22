============
Installation
============

Requirements
------------

============== ==================================================
Python         3.10 -- 3.13
Django         5.2 LTS or 6.0 (6.0 needs Python 3.12+)
Database       anything Django supports
============== ==================================================

The following are installed automatically as dependencies: django-dsl_,
djangoql-iplweb_, django-tables2_, tablib_, lxml_, pypandoc_ and bleach_.

.. _django-dsl: https://pypi.org/project/django-dsl/
.. _djangoql-iplweb: https://pypi.org/project/djangoql-iplweb/
.. _django-tables2: https://github.com/jieter/django-tables2
.. _tablib: https://tablib.readthedocs.io/
.. _lxml: https://lxml.de/
.. _pypandoc: https://pypi.org/project/pypandoc/
.. _bleach: https://pypi.org/project/bleach/

Install the package
-------------------

.. code-block:: console

    $ pip install django-flexible-reports

Or, with uv_:

.. code-block:: console

    $ uv add django-flexible-reports

.. _uv: https://docs.astral.sh/uv/

Configure the project
---------------------

Add the app -- and ``django_tables2``, which does the actual rendering -- to
``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        "django.contrib.admin",          # to edit report definitions
        "django.contrib.contenttypes",   # required: models point at ContentType
        ...
        "django_tables2",
        "flexible_reports",
    ]

``"flexible_reports.apps.FlexibleReportsConfig"`` also works; it is the same
app config Django picks up by default.

Enable the ``request`` context processor. ``{% flexible %}`` hands the
surrounding template context to the django-tables2 adapter, which needs
``request`` in it:

.. code-block:: python

    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            ...
            "OPTIONS": {
                "context_processors": [
                    ...
                    "django.template.context_processors.request",
                ],
            },
        },
    ]

Then create the tables:

.. code-block:: console

    $ python manage.py migrate

No URLconf changes
------------------

.. note::

   There is **nothing to add to your URLconf**. ``flexible_reports.urls``
   exists but its ``urlpatterns`` is empty and ``flexible_reports.views`` is
   empty too -- the app ships no views. You render reports from your own
   views (see :doc:`quickstart`).

   Older versions of this documentation told you to write
   ``url(r'^', include(flexible_reports_urls))``. That advice was doubly
   wrong: it achieved nothing, and ``django.conf.urls.url`` was removed in
   Django 4.0.

Optional extras
---------------

grappelli
    If django-grappelli_ is installed, ``flexible_reports.admin.helpers``
    detects it at import time and the ``Column``, ``ColumnOrder`` and
    ``ReportElement`` inlines become drag-and-drop sortable. Nothing needs to
    be configured. Without grappelli the inlines simply show a numeric
    *Position* field.

pandoc
    Exporting a report to ``.docx`` shells out to pandoc_ through
    ``pypandoc``, so the ``pandoc`` binary has to be present on the machine
    (``apt install pandoc``, ``brew install pandoc``). HTML and tablib
    (XLSX/CSV/…) exports need nothing extra.

.. _django-grappelli: https://github.com/sehmaschine/django-grappelli
.. _pandoc: https://pandoc.org/
