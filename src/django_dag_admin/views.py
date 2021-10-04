from django.contrib.admin.views.main import (
    ChangeList, IGNORED_PARAMS as BASE_IGNORED_PARAMS
)
from django.core.paginator import InvalidPage
from django.contrib.admin.options import IncorrectLookupParameters
from django.db.models import Count, F, Q
from django.db.models import Exists
from django.db.models import OuterRef, Subquery
from django.contrib.admin.views.main import (
    ALL_VAR, ORDER_VAR, PAGE_VAR, SEARCH_VAR, IS_POPUP_VAR, TO_FIELD_VAR
)
# Additional changelist settings
LAYOUT_VAR = 'sty'
IGNORED_PARAMS = BASE_IGNORED_PARAMS + (LAYOUT_VAR, )
TREE_LAYOUT = 'tree'
LIST_LAYOUT = 'list'
ORDERED_DAG_SEQUENCE_FIELD_NAME = '_sequence'


class DagChangeList(ChangeList):
    def allow_node_drag(self, request):
        draggable = True
        for k, v in self.params.items():
            if k in [ALL_VAR, IS_POPUP_VAR, TO_FIELD_VAR, PAGE_VAR]:
                continue
            elif ORDER_VAR == k:
                if v != '' and self.model.sequence_manager:  # Sorted nodes thefore disable is sort enabled
                    draggable = False
            elif SEARCH_VAR == k:
                if v != '':
                    draggable = False  # disbaled moving nodes if filters are active
            elif LAYOUT_VAR == k:
                if v != TREE_LAYOUT:
                    draggable = False  # disable is not in tree view
        return draggable

    # Copied from Django "version": "==2.2.19"
    # Changed: IGNORED_PARAMS is updated to include LAYOUT_VAR
    def get_filters_params(self, params=None):
        """
        Return all params except IGNORED_PARAMS.
        """
        params = params or self.params
        lookup_params = params.copy()  # a dictionary of the query string
        # Remove all the parameters that are globally and systematically
        # ignored.
        for ignored in IGNORED_PARAMS:
            if ignored in lookup_params:
                del lookup_params[ignored]
        return lookup_params

    def _convert_order_node_to_edge(self, ordering):
        for part in ordering:
            if isinstance(part, str):
                order_type = part[:part.startswith('-')]
                base = part.lstrip('-')
            elif isinstance(part, F):
                base = part.name
                order_type = ''
            if base == ORDERED_DAG_SEQUENCE_FIELD_NAME:
                yield part
            else:
                yield "{}child__{}".format(order_type, base)

    def get_results_tree(self, request):
        qs = self.queryset \
            .annotate(
                children_count=Count('children', distinct=True),
                usage_count=Subquery(
                    self.model.get_node_model().objects
                        .filter(pk=OuterRef('id'))
                        .annotate(usage_count=Count('parents__pk'))
                        .values('usage_count')
                )
            )
        qs = self.apply_select_related(qs)
        ordering = self.get_ordering(request, qs)
        if self.model.sequence_manager:
            ordering = ['dag_sequence_path', ]
        else:
            ordering = ['dag_pk_path', ]
        qs = qs.order_by(*ordering)
        return qs

    def get_results_edgetree(self, request):
        qs = (
            self.model.get_edge_model()
                .objects
                .filter(Q(child_id__in=self.queryset.values('pk')))
                .annotate(
                    siblings_count=Count('parent__children', distinct=True),
                    is_child=Count('parent__parents'),
                    children_count=Count('child__children', distinct=True),
                    parent_used=Exists(self.queryset.filter(pk=OuterRef('parent_id')))
            ))
        if not qs.query.select_related:
            qs = self.apply_select_related(qs, for_edge=True)

        if self.model.sequence_manager:
            order_component = self.model.sequence_manager \
                .get_edge_rel_sort_query_component(self.model, 'child', 'parent')
            qs = qs.annotate(**{ORDERED_DAG_SEQUENCE_FIELD_NAME: order_component})

        # Set ordering.
        ordering = list(self._convert_order_node_to_edge(self.get_ordering(request, qs,)))
        qs = qs.order_by(*ordering)
        return qs

    def get_results_list(self, request):
        qs = self.queryset.annotate(
                children_count=Count('children', distinct=True),
                usage_count=Subquery(
                    self.model.get_node_model()
                        .objects
                        .filter(pk=OuterRef('id'))
                        .annotate(usage_count=Count('parents__pk'))
                        .values('usage_count')
                )
            )
        qs = self.apply_select_related(qs)
        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)
        return qs

    def get_results(self, request):
        self.result_list_extra = []

        # Add annotation to show detached nodes here
        # to self.queryset look for no parent matching path / parents
        if self.get_layout_style(request) == LIST_LAYOUT:
            qs = self.get_results_list(request)
        else:
            qs = self.get_results_tree(request)

        paginator = self.model_admin.get_paginator(request, qs, self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count

        # Get the total number of objects, with no admin filters applied.
        if self.model_admin.show_full_result_count:
            full_result_count = self.root_queryset.count()
        else:
            full_result_count = None
        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and can_show_all) or not multi_page:
            result_list = qs._clone()
        else:
            try:
                result_list = paginator.page(self.page_num + 1).object_list
            except InvalidPage:
                raise IncorrectLookupParameters

        self.result_count = result_count
        self.show_full_result_count = self.model_admin.show_full_result_count
        # Admin actions are shown if there is at least one entry
        # or if entries are not counted because show_full_result_count is disabled
        self.show_admin_actions = not self.show_full_result_count or bool(full_result_count)
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator

    def _get_default_layout_style(self):
        layout_style = 'tree'
        if hasattr(self.model_admin, 'layout_style'):
            layout_style = self.model_admin.layout_style
        return layout_style

    def get_layout_style(self, request):
        params = self.params
        return params.get(LAYOUT_VAR, None) or self._get_default_layout_style()

    def _get_default_ordering(self):
        ordering = []
        if self.model_admin.ordering:
            ordering = self.model_admin.ordering
        elif self.lookup_opts.ordering:
            ordering = self.lookup_opts.ordering
        return ordering

    def apply_select_related(self, qs, for_edge=False):
        if self.list_select_related is True:
            if for_edge:
                return qs.select_related()
            return qs.select_related()

        if self.list_select_related is False:
            if self.has_related_field_in_list_display():
                return qs.select_related()
            if for_edge:
                return qs.select_related()
            return qs

        if self.list_select_related:
            if for_edge:
                related = ["child__{}".format(relation) for relation in self.list_select_related]
                return qs.select_related(*related)
            return qs.select_related(*self.list_select_related)
        return qs
