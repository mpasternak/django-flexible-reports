"""A deliberately tiny reportable domain: authors and their books.

Small on purpose, but not degenerate -- ``Book.author`` is a foreign key, so
the demo report can exercise a column whose ``attr_name`` uses dot notation
(``author.name``) and a django-dsl query that reaches across the relation.
"""

from django.db import models


class Author(models.Model):
    name = models.CharField("Name", max_length=200, unique=True)
    country = models.CharField("Country", max_length=100, blank=True)

    class Meta:
        verbose_name = "Author"
        verbose_name_plural = "Authors"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Book(models.Model):
    #: Shorthands usable in django-dsl queries. ``flexible_reports`` looks for
    #: this attribute (``flexible_reports.constants.SHORTCUTS_ATTR_NAME``) on
    #: the datasource's base model, so a datasource can say
    #: ``author = "Stanislaw Lem"`` instead of ``author__name = "..."``.
    django_dsl_shortcuts = {
        "author": "author__name",
        "country": "author__country",
    }

    title = models.CharField("Title", max_length=300)
    author = models.ForeignKey(
        Author,
        verbose_name="Author",
        related_name="books",
        on_delete=models.CASCADE,
    )
    year = models.PositiveIntegerField("Year of publication")
    pages = models.PositiveIntegerField("Pages")
    price = models.DecimalField("Price", max_digits=7, decimal_places=2)

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ("title",)
        unique_together = (("title", "author"),)

    def __str__(self):
        return f"{self.title} ({self.year})"
