# -*- coding: utf-8
from __future__ import absolute_import, unicode_literals

from django.conf.urls import include, url
from django.contrib import admin
from flexible_reports.urls import urlpatterns as flexible_reports_urls

admin.autodiscover()

urlpatterns = [
    url(r'^admin/', admin.site.urls)
]
