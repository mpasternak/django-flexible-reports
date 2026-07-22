from django.apps import apps
from django.contrib import admin
from django.urls import include, path

from demoapp import views

urlpatterns = []

# Only routed for the grappelli flavour. Grappelli's related-object lookups
# and autocompletes call these views, so forgetting them leaves a half-broken
# admin.
if apps.is_installed("grappelli"):
    urlpatterns += [path("grappelli/", include("grappelli.urls"))]

urlpatterns += [
    path("admin/", admin.site.urls),
    path("", views.index, name="demo-index"),
]
