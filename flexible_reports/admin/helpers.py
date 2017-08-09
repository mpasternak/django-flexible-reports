# -*- encoding: utf-8 -*-
from django.forms.widgets import Textarea

SmallerTextarea = Textarea(attrs={'cols': 75, 'rows': 2})
AverageTextarea = Textarea(attrs={'cols': 75, 'rows': 4})
BiggerTextarea = Textarea(attrs={'cols': 75, 'rows': 18})

try:
    from grappelli.forms import GrappelliSortableHiddenMixin as \
        SortableHiddenMixin
except ImportError:
    class SortableHiddenMixin:
        # no-op
        pass
