"""The one page that proves the library works end to end.

Rendering a report takes exactly three steps:

1. fetch the :class:`~flexible_reports.models.report.Report`,
2. hand it the queryset every datasource will narrow down
   (``set_base_queryset``) and, optionally, the context its parametrised
   queries are rendered with (``set_context``),
3. put it through the ``{% flexible %}`` template tag.

Everything else -- which tables exist, which columns they have, how they are
sorted, how the cells are formatted -- lives in the database and is edited in
the admin.
"""

from django.conf import settings
from django.shortcuts import render

from flexible_reports.models import Report

from .models import Book


def index(request):
    report = Report.objects.filter(slug=settings.DEMO_REPORT_SLUG).first()

    if report is not None:
        # The datasources filter *this* queryset; nothing outside of it can
        # ever show up in the report.
        report.set_base_queryset(Book.objects.select_related("author"))
        # Values for the ``{{ min_pages }}`` placeholder inside the DjangoQL
        # datasource query.
        report.set_context({"min_pages": settings.DEMO_MIN_PAGES})

    return render(
        request,
        "demo/index.html",
        {
            "report": report,
            "report_slug": settings.DEMO_REPORT_SLUG,
            "min_pages": settings.DEMO_MIN_PAGES,
            "book_count": Book.objects.count(),
            "grappelli": "grappelli" in settings.INSTALLED_APPS,
        },
    )
