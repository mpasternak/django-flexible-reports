# -*- coding: utf-8 -*-

"""Naming helpers shared by :meth:`Table.clone` and :meth:`Report.clone`.

The suffix appended to a clone's name is translatable: the ``msgid`` is
``"copy"``, so an English deployment gets ``"My table (copy)"`` and a Polish
one ``"My table (kopia)"``.
"""

import re

from django.utils.text import slugify

try:
    from django.utils.translation import gettext as _
except ImportError:  # pragma: no cover
    from django.utils.translation import ugettext as _

__all__ = [
    "copy_word",
    "strip_copy_suffix",
    "make_copy_label",
    "next_free_label",
    "strip_slug_copy_suffix",
    "make_copy_slug",
    "next_free_slug",
]

#: Fallback used when the active translation of ``"copy"`` slugifies to an
#: empty string (a language written entirely in non-latin script).
DEFAULT_SLUG_WORD = "copy"


def copy_word():
    """The translated word used to build clone names.

    Resolved at call time, so it follows the currently active language.
    """
    return _("copy")


def strip_copy_suffix(label):
    """Strip a trailing ``" (copy)"`` / ``" (copy 7)"`` from ``label``.

    Cloning a clone should give ``"X (copy 2)"``, not ``"X (copy) (copy)"``.
    The pattern is built from the *current* translation, so a label produced
    under a different active language will simply not match and we end up with
    a nested suffix -- a cosmetic, accepted degradation.
    """
    pattern = re.compile(r"\s*\(%s(?:\s+\d+)?\)\s*$" % re.escape(copy_word()))
    return pattern.sub("", label).strip()


def make_copy_label(stem, number):
    """``("X", 1) -> "X (copy)"``, ``("X", 2) -> "X (copy 2)"``."""
    if number <= 1:
        return "%s (%s)" % (stem, copy_word())
    return "%s (%s %d)" % (stem, copy_word(), number)


def next_free_label(queryset, field_name, value):
    """First unused ``"<value> (copy N)"`` for ``field_name`` in ``queryset``.

    The scan races: two concurrent clones can compute the same name. No field
    involved has ``unique=True``, so nothing blows up -- we would simply end up
    with two identically named objects. Cloning is a manual administrative
    operation, so this is accepted.
    """
    stem = strip_copy_suffix(value)
    number = 1
    while True:
        candidate = make_copy_label(stem, number)
        if not queryset.filter(**{field_name: candidate}).exists():
            return candidate
        number += 1


def _slug_copy_word():
    return slugify(copy_word()) or DEFAULT_SLUG_WORD


def strip_slug_copy_suffix(slug):
    """Slug counterpart of :func:`strip_copy_suffix` (``-copy``, ``-copy-3``)."""
    pattern = re.compile(r"-%s(?:-\d+)?$" % re.escape(_slug_copy_word()))
    return pattern.sub("", slug)


def make_copy_slug(stem, number, max_length):
    """Append ``-copy`` / ``-copy-N`` to ``stem``, truncating the *stem*.

    Truncating the whole string would chop the suffix off and make the clone's
    slug collide with the source's again, so the stem is shortened to make room
    for the suffix instead.
    """
    word = _slug_copy_word()
    suffix = "-%s" % word if number <= 1 else "-%s-%d" % (word, number)
    if max_length is not None:
        stem = stem[: max(max_length - len(suffix), 0)].rstrip("-")
    return "%s%s" % (stem, suffix)


def next_free_slug(queryset, field_name, value, max_length):
    """First unused ``"<value>-copy-N"`` for ``field_name`` in ``queryset``."""
    stem = strip_slug_copy_suffix(value)
    number = 1
    while True:
        candidate = make_copy_slug(stem, number, max_length)
        if not queryset.filter(**{field_name: candidate}).exists():
            return candidate
        number += 1
