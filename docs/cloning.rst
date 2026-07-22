========
Cloning
========

Report definitions get elaborate, and the usual way to build the next one is to
start from the last one. ``Table`` and ``Report`` therefore know how to copy
themselves.

.. versionadded:: 0.4.0

From the admin
==============

Open a ``Table`` or a ``Report`` change form and press **Clone** in the
object-tools bar (next to *History*). You land on the change form of the fresh
copy, an entry is written to the admin history, and a success message names the
new object.

The button posts to ``<pk>/clone/`` under the model's admin URLs. It is a POST
behind a CSRF token on purpose -- a GET link would let a foreign page create
objects through an ``<img src="...">``. Permissions: *add* on the model plus
*view* on the source object (*change* on the source is deliberately not
required, matching the built-in "Save as new").

The mixin providing all of this is ``flexible_reports.admin.CloneAdminMixin``;
it works with both the stock admin and grappelli.

From code
=========

.. code-block:: python

    new_table = table.clone()
    new_report = report.clone()

Both run in a transaction and return the newly created object. **Neither
modifies the source**: after the call ``table.pk`` is unchanged and a later
``table.save()`` still updates the original.

What is copied
==============

``Table.clone()``
    The table itself, all of its ``Column`` rows, and all of its
    ``ColumnOrder`` rows -- with both foreign keys repointed, so the copy sorts
    by *its own* columns. Reports using the original table are left alone.

``Report.clone()``
    The report itself and all of its ``ReportElement`` rows. The copy is
    **shallow**: cloned elements point at the very same ``Table`` and
    ``Datasource`` objects as the original. If you want an independent table,
    clone the table separately and repoint the element.

    Element slugs are kept as they are. They cannot collide (uniqueness is per
    report) and the copied layout template addresses elements by slug, so
    renaming them would break it.

``Datasource`` has no ``clone()``. Duplicating one is a matter of copying its
query into a new object.

Naming
======

The copy gets a ``(copy)`` suffix, and cloning a copy counts up rather than
nesting:

.. code-block:: text

    "Books"            ->  "Books (copy)"
    "Books (copy)"     ->  "Books (copy 2)"
    "Books (copy 2)"   ->  "Books (copy 3)"

Slugs follow the same shape (``library-report`` → ``library-report-copy``),
except that the *stem* is truncated to make room for the suffix, so a maximum
length slug does not lose its suffix and collide with the source again.

The word "copy" is translatable (msgid ``"copy"``), resolved against the
language active at the time of the call: a Polish admin produces
``"Books (kopia)"``. If the translation slugifies to nothing (a language in a
non-latin script), slugs fall back to the literal ``copy``.

The helpers live in ``flexible_reports.models.cloning`` and are reusable:
``copy_word``, ``strip_copy_suffix``, ``make_copy_label``, ``next_free_label``,
``strip_slug_copy_suffix``, ``make_copy_slug``, ``next_free_slug``.

.. note::

   Finding the first free name is a scan, so two clones started at the very
   same moment can compute the same name. None of the fields involved is
   ``unique``, so nothing breaks -- you simply end up with two identically
   named objects. Cloning is a manual administrative action, so this is
   accepted rather than locked against.
