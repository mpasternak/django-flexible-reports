"""Populate the demo database.

Idempotent on purpose: run it as often as you like. Sample data is upserted
and the report definition is rebuilt from scratch every time, so editing the
report in the admin and then re-running this command gets you back to a known
state.

What gets created:

* a superuser (``admin`` / ``admin``),
* a handful of :class:`~demoapp.models.Author` and
  :class:`~demoapp.models.Book` rows,
* two :class:`~flexible_reports.models.datasource.Datasource` objects -- one
  per supported query language, one of them parametrised,
* one :class:`~flexible_reports.models.table.Table` with six
  :class:`~flexible_reports.models.column.Column` objects (dot-notation
  accessor, custom cell templates, column totals) and its sort order,
* a :class:`~flexible_reports.models.report.Report` with three elements, the
  last of which uses the "except catchall" mode.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from flexible_reports.models import (
    Column,
    ColumnOrder,
    Datasource,
    Report,
    ReportElement,
    Table,
)
from flexible_reports.models.report import (
    DATA_FROM_DATASOURCE,
    DATA_FROM_EXCEPT_CATCHALL,
)
from flexible_reports.models.table import SortWithOtherTables
from flexible_reports.query_backends import DJANGOQL, DSL

from demoapp.models import Author, Book

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
ADMIN_EMAIL = "admin@example.com"

TABLE_LABEL = "Books"
DATASOURCE_LONG = "Long books (over {{ min_pages }} pages)"
DATASOURCE_LEGUIN = "Everything by Ursula K. Le Guin"

AUTHORS = [
    ("Ursula K. Le Guin", "USA"),
    ("Stanisław Lem", "Poland"),
    ("Terry Pratchett", "United Kingdom"),
]

# (title, author, year, pages, price)
BOOKS = [
    ("A Wizard of Earthsea", "Ursula K. Le Guin", 1968, 183, "24.00"),
    ("The Left Hand of Darkness", "Ursula K. Le Guin", 1969, 304, "42.50"),
    ("The Dispossessed", "Ursula K. Le Guin", 1974, 341, "39.90"),
    ("Solaris", "Stanisław Lem", 1961, 204, "29.90"),
    ("The Cyberiad", "Stanisław Lem", 1965, 295, "34.50"),
    ("His Master's Voice", "Stanisław Lem", 1968, 199, "31.00"),
    ("Mort", "Terry Pratchett", 1987, 272, "27.50"),
    ("Guards! Guards!", "Terry Pratchett", 1989, 376, "45.00"),
    ("Small Gods", "Terry Pratchett", 1992, 400, "38.00"),
    ("Going Postal", "Terry Pratchett", 2004, 484, "49.90"),
]


class Command(BaseCommand):
    help = "Create the demo superuser, sample books and the demo report."

    @transaction.atomic
    def handle(self, *args, **options):
        self._create_superuser()
        self._create_books()
        report = self._create_report()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready: %d authors, %d books, report %r with %d elements."
                % (
                    Author.objects.count(),
                    Book.objects.count(),
                    report.slug,
                    report.reportelement_set.count(),
                )
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Log into the admin as %s / %s" % (ADMIN_USERNAME, ADMIN_PASSWORD)
            )
        )

    # ------------------------------------------------------------------ data

    def _create_superuser(self):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=ADMIN_USERNAME,
            defaults={"email": ADMIN_EMAIL},
        )
        # Re-set unconditionally: the point of the demo account is that its
        # password is known.
        user.is_staff = True
        user.is_superuser = True
        user.set_password(ADMIN_PASSWORD)
        user.save()
        self.stdout.write(
            "%s superuser %r" % ("Created" if created else "Updated", ADMIN_USERNAME)
        )

    def _create_books(self):
        authors = {}
        for name, country in AUTHORS:
            author, _created = Author.objects.update_or_create(
                name=name, defaults={"country": country}
            )
            authors[name] = author

        for title, author_name, year, pages, price in BOOKS:
            Book.objects.update_or_create(
                title=title,
                author=authors[author_name],
                defaults={
                    "year": year,
                    "pages": pages,
                    "price": Decimal(price),
                },
            )

        self.stdout.write(
            "Sample data: %d authors, %d books"
            % (Author.objects.count(), Book.objects.count())
        )

    # -------------------------------------------------------- report defintion

    def _create_report(self):
        book_ct = ContentType.objects.get_for_model(Book)

        # Rebuild from scratch, so re-running the command undoes whatever was
        # changed in the admin. Deleting the table cascades to its columns,
        # its column order and the report elements pointing at it.
        Report.objects.filter(slug=settings.DEMO_REPORT_SLUG).delete()
        Table.objects.filter(label=TABLE_LABEL).delete()
        Datasource.objects.filter(
            label__in=[DATASOURCE_LONG, DATASOURCE_LEGUIN]
        ).delete()

        datasource_long = self._make_datasource(
            label=DATASOURCE_LONG,
            base_model=book_ct,
            # DjangoQL, parametrised: ``{{ min_pages }}`` is rendered against
            # the context the view passes to ``Report.set_context()``.
            # ``sample_context`` supplies a value for the validation query run
            # on save.
            query_language=DJANGOQL,
            dsl_query="pages > {{ min_pages }}",
            sample_context={"min_pages": settings.DEMO_MIN_PAGES},
        )

        datasource_leguin = self._make_datasource(
            label=DATASOURCE_LEGUIN,
            base_model=book_ct,
            # django-dsl, using the ``django_dsl_shortcuts`` declared on the
            # Book model: ``author`` expands to ``author__name``.
            query_language=DSL,
            dsl_query='author = "Ursula K. Le Guin"',
            sample_context={},
        )

        table = self._make_table(book_ct)

        report = Report.objects.create(
            title="Library report",
            slug=settings.DEMO_REPORT_SLUG,
            # ``template`` is left at its default, which is the source of
            # ``flexible_reports/templates/flexible_reports/report.html``.
            # Edit it in the admin to change the report's layout.
        )

        ReportElement.objects.create(
            parent=report,
            position=0,
            title="Long books (over %d pages)" % settings.DEMO_MIN_PAGES,
            slug="long-books",
            data_from=DATA_FROM_DATASOURCE,
            datasource=datasource_long,
            table=table,
        )
        ReportElement.objects.create(
            parent=report,
            position=1,
            title="Everything by Ursula K. Le Guin",
            slug="le-guin",
            data_from=DATA_FROM_DATASOURCE,
            datasource=datasource_leguin,
            table=table,
        )
        # "Except catchall": whatever none of the datasources above caught.
        # No datasource, just the base model.
        ReportElement.objects.create(
            parent=report,
            position=2,
            title="Everything else",
            slug="everything-else",
            data_from=DATA_FROM_EXCEPT_CATCHALL,
            datasource=None,
            base_model=book_ct,
            table=table,
        )

        self.stdout.write("Report definition rebuilt")
        return report

    def _make_datasource(self, **kwargs):
        datasource = Datasource(**kwargs)
        # Validates the query against the base model -- if the demo ships a
        # broken query, seeding fails loudly instead of producing an empty
        # report.
        datasource.full_clean()
        datasource.save()
        return datasource

    def _make_table(self, book_ct):
        table = Table(
            label=TABLE_LABEL,
            base_model=book_ct,
            sort_option=SortWithOtherTables.id,
            attrs={"class": "report-table"},
            empty_template="No books match this query.",
        )
        table.full_clean()
        table.save()

        # A column is either "attribute driven" (``attr_name``) or "template
        # driven" (``template``) or both -- the template gets ``value``
        # (resolved through ``attr_name``) and ``record`` (the model
        # instance).
        columns = {}
        specs = [
            dict(
                # No accessor at all: purely a template, using the row counter
                # django-tables2 provides. Not sortable (nothing to sort by),
                # but it still shows a total -- the row count.
                label="Nr",
                attr_name=None,
                template="{{ row_counter|add:1 }}",
                sortable=False,
                display_totals=True,
                footer_template="{{ count }} book(s)",
                attrs={"th": {"class": "col-nr"}, "td": {"class": "col-nr"}},
            ),
            dict(
                # Custom template combining the resolved value with another
                # attribute of the record.
                label="Title",
                attr_name="title",
                template=(
                    "<strong>{{ value }}</strong><br>"
                    "<small>{{ record.pages }} pages</small>"
                ),
                sortable=True,
            ),
            dict(
                # Dot notation walks the foreign key.
                label="Author",
                attr_name="author.name",
                template="{{ value }}",
                sortable=True,
            ),
            dict(
                label="Country",
                attr_name="author.country",
                template="{{ value }}",
                sortable=True,
            ),
            dict(
                label="Year",
                attr_name="year",
                template="{{ value }}",
                sortable=True,
            ),
            dict(
                # Totals over a numeric column: the footer gets the sum in
                # ``value`` and the row count in ``count``.
                label="Price",
                attr_name="price",
                template="{{ value|floatformat:2 }} PLN",
                sortable=True,
                display_totals=True,
                footer_template="{{ value|floatformat:2 }} PLN",
                attrs={"th": {"class": "col-num"}, "td": {"class": "col-num"}},
            ),
        ]

        for position, spec in enumerate(specs):
            column = Column(parent=table, position=position, **spec)
            column.full_clean()
            column.save()
            columns[spec["label"]] = column

        # Default ordering of the table: newest first, then alphabetically.
        for position, (label, desc) in enumerate([("Year", True), ("Title", False)]):
            ColumnOrder.objects.create(
                table=table,
                column=columns[label],
                desc=desc,
                position=position,
            )

        self.stdout.write(
            "Table %r rebuilt with %d columns" % (TABLE_LABEL, len(specs))
        )
        return table
