# -*- encoding: utf-8 -*-

try:
    from grappelli.forms import GrappelliSortableHiddenMixin as \
        SortableHiddenMixin
except ImportError:
    class SortableHiddenMixin:
        # no-op
        pass
