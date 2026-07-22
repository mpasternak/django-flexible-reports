"""Demo flavour #2: the same project behind django-grappelli.

    python demo/manage.py runserver 127.0.0.1:8001 \\
        --settings=demo.settings_grappelli

``django-grappelli`` is *not* a dependency of django-flexible-reports; install
it yourself (``pip install django-grappelli`` / ``uv run --with
django-grappelli ...``) before using this module.

Two things matter here and are easy to get wrong:

1. ``grappelli`` must come **before** ``django.contrib.admin`` in
   ``INSTALLED_APPS``. Both ship ``admin/*.html``; with the app dirs template
   loader the first app wins, so putting grappelli second silently gives you
   the vanilla admin.
2. ``grappelli.urls`` has to be routed (see ``demo/urls.py``), otherwise the
   related-object lookups and the autocomplete widgets 404.

With grappelli installed, ``flexible_reports.admin.helpers`` automatically
picks up ``GrappelliSortableHiddenMixin``, so the drag-and-drop reordering of
columns and report elements starts working with no further configuration.
"""

from .settings_base import *  # noqa: F401,F403
from .settings_base import INSTALLED_APPS

INSTALLED_APPS = ["grappelli"] + INSTALLED_APPS

GRAPPELLI_ADMIN_TITLE = "django-flexible-reports demo"
