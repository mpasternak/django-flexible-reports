#!/usr/bin/env python
"""Entry point for the django-flexible-reports demo project.

Two settings modules are available:

* ``demo.settings_django``    -- plain ``django.contrib.admin`` (the default),
* ``demo.settings_grappelli`` -- the same project with django-grappelli.

Pick one with ``--settings=`` or ``DJANGO_SETTINGS_MODULE``.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent


def main():
    # ``demo/`` itself so that ``demo`` and ``demoapp`` are importable...
    sys.path.insert(0, str(HERE))
    # ...and the repository root, so the demo always exercises the working
    # copy of ``flexible_reports`` rather than a release installed in the
    # environment.
    sys.path.insert(0, str(REPO_ROOT))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings_django")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
