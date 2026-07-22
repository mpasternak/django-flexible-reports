from django.contrib import admin

from .models import Author, Book


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "book_count"]
    search_fields = ["name", "country"]

    @admin.display(description="Books")
    def book_count(self, obj):
        return obj.books.count()


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "year", "pages", "price"]
    list_filter = ["author", "year"]
    search_fields = ["title", "author__name"]
