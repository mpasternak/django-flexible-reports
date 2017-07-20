# -*- coding: utf-8 -*-
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    UpdateView,
    ListView
)

from .models import (
	Column,
	Table,
	Report,
	Collection,
)


class ColumnCreateView(CreateView):

    model = Column


class ColumnDeleteView(DeleteView):

    model = Column


class ColumnDetailView(DetailView):

    model = Column


class ColumnUpdateView(UpdateView):

    model = Column


class ColumnListView(ListView):

    model = Column


class TableCreateView(CreateView):

    model = Table


class TableDeleteView(DeleteView):

    model = Table


class TableDetailView(DetailView):

    model = Table


class TableUpdateView(UpdateView):

    model = Table


class TableListView(ListView):

    model = Table


class ReportCreateView(CreateView):

    model = Report


class ReportDeleteView(DeleteView):

    model = Report


class ReportDetailView(DetailView):

    model = Report


class ReportUpdateView(UpdateView):

    model = Report


class ReportListView(ListView):

    model = Report


class CollectionCreateView(CreateView):

    model = Collection


class CollectionDeleteView(DeleteView):

    model = Collection


class CollectionDetailView(DetailView):

    model = Collection


class CollectionUpdateView(UpdateView):

    model = Collection


class CollectionListView(ListView):

    model = Collection

