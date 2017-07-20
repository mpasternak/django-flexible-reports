# -*- coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url, include

from flexible_reports.urls import urlpatterns as flexible_reports_urls

urlpatterns = [
    url(r'^', include(flexible_reports_urls, namespace='flexible_reports')),
]
