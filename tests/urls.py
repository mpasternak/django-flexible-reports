# -*- coding: utf-8
from __future__ import absolute_import, unicode_literals

try:
    from django.urls import re_path as url
except ImportError:
    from django.conf.urls import url

from django.contrib import admin

admin.autodiscover()

urlpatterns = [url(r"^admin/", admin.site.urls)]
