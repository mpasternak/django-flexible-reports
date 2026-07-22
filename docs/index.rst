=======================
Django Flexible Reports
=======================

A framework for **database-defined reports** in Django.

Instead of hardcoding a report in a template or a view, you describe it in the
database -- which rows it shows, which columns it has, how the cells are
formatted, how it is sorted -- and edit all of that through the Django admin.
Your application code only picks a report, hands it a queryset and renders it
with one template tag:

.. code-block:: django

    {% load flexible_reports_tags %}
    {% flexible report %}

Rendering is done by django-tables2_, so sortable headers, footers with totals
and export to other formats come for free.

.. _django-tables2: https://github.com/jieter/django-tables2

Where to start
--------------

* :doc:`installation` -- what to add to ``INSTALLED_APPS`` (and what *not* to).
* :doc:`quickstart` -- a complete report, from an empty project to a rendered page.
* :doc:`concepts` -- the data model, in detail.
* :doc:`demo` -- a runnable example shipped with the source.

.. toctree::
   :maxdepth: 2
   :caption: User guide

   installation
   quickstart
   concepts
   queries
   rendering
   exporting
   cloning
   demo

.. toctree::
   :maxdepth: 1
   :caption: Project

   contributing
   authors
   history

Indices
-------

* :ref:`genindex`
* :ref:`search`
