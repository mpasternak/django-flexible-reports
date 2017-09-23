=============================
Django Flexible Reports
=============================

.. image:: https://badge.fury.io/py/django-flexible-reports.svg
    :target: https://badge.fury.io/py/django-flexible-reports

.. image:: https://travis-ci.org/mpasternak/django-flexible-reports.svg?branch=master
    :target: https://travis-ci.org/mpasternak/django-flexible-reports

.. image:: https://coveralls.io/repos/github/mpasternak/django-flexible-reports/badge.svg?branch=master
   :target: https://coveralls.io/github/mpasternak/django-flexible-reports?branch=master

A framework for report generation in Django

Documentation
-------------

The full documentation is at https://django-flexible-reports.readthedocs.io.

Quickstart
----------

Install Django Flexible Reports::

    pip install django-flexible-reports

Add it to your `INSTALLED_APPS`:

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

Features
--------

* TODO

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
