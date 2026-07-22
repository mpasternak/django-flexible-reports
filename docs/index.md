# Django Flexible Reports

A framework for **database-defined reports** in Django.

Instead of hardcoding a report in a template or a view, you describe it in the
database -- which rows it shows, which columns it has, how the cells are
formatted, how it is sorted -- and edit all of that through the Django admin.
Your application code only picks a report, hands it a queryset and renders it
with one template tag:

```django
{% load flexible_reports_tags %}
{% flexible report %}
```

Rendering is done by [django-tables2][django-tables2], so sortable headers,
footers with totals and export to other formats come for free.

[django-tables2]: https://github.com/jieter/django-tables2

## Where to start

* [Installation](installation.md) -- what to add to `INSTALLED_APPS` (and what *not* to).
* [Quickstart](quickstart.md) -- a complete report, from an empty project to a rendered page.
* [The data model](concepts.md) -- the data model, in detail.
* [The demo project](demo.md) -- a runnable example shipped with the source.
