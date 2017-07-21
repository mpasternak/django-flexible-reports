# -*- coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url, include
from django.contrib import admin

from flexible_reports.urls import urlpatterns as flexible_reports_urls

admin.autodiscover()

urlpatterns = [
    url(r'^', include(flexible_reports_urls, namespace='flexible_reports')),
    url(r'^admin/', include(admin.site.urls)),
]
