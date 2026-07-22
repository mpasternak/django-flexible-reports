# -*- coding: utf-8 -*-
#
# Sphinx configuration for the django-flexible-reports documentation.
#
# The docs are pure prose -- nothing here imports Django or touches a database,
# so the build needs only Sphinx, the theme and this package on ``sys.path``.

import os
import sys
from datetime import date

# ``docs/`` -> repository root, so that ``import flexible_reports`` works even
# when the package is not installed.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flexible_reports  # noqa: E402

# -- Project information -----------------------------------------------------

project = "Django Flexible Reports"
author = "Michał Pasternak"
copyright = "2017-%d, %s" % (date.today().year, author)

version = flexible_reports.__version__
release = flexible_reports.__version__

# -- General configuration ---------------------------------------------------

extensions = []

source_suffix = {".rst": "restructuredtext"}
root_doc = "index"

# ``superpowers/`` is an archive of design specs and plans kept next to the
# docs on purpose; it is not part of the manual and must not be built.
exclude_patterns = [
    "_build",
    "superpowers",
    "Thumbs.db",
    ".DS_Store",
]

# Single backquotes in the prose here always mean "literal".
default_role = "literal"

pygments_style = "sphinx"

# -- HTML output -------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_title = "%s %s" % (project, release)
htmlhelp_basename = "django-flexible-reportsdoc"

# No custom static files or templates are shipped; pointing Sphinx at
# non-existent directories (``_static``, ``_templates``) only produces
# warnings, so neither ``html_static_path`` nor ``templates_path`` is set.

# -- LaTeX / man / texinfo output --------------------------------------------

latex_documents = [
    (
        root_doc,
        "django-flexible-reports.tex",
        "Django Flexible Reports Documentation",
        author,
        "manual",
    ),
]

man_pages = [
    (
        root_doc,
        "django-flexible-reports",
        "Django Flexible Reports Documentation",
        [author],
        1,
    )
]

texinfo_documents = [
    (
        root_doc,
        "django-flexible-reports",
        "Django Flexible Reports Documentation",
        author,
        "django-flexible-reports",
        "A framework for database-defined reports in Django.",
        "Miscellaneous",
    ),
]
