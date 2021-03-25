from django.contrib.admin.views.main import (
    ChangeList,  IGNORED_PARAMS as BASE_IGNORED_PARAMS
)
from django.db.models import Count, F, Value, Min, Q
from django.db.models.functions import Coalesce
from django.db.models import Exists
from django.db.models import OuterRef, Subquery
from django.db.models import ExpressionWrapper, F, IntegerField, TextField
from django.contrib.admin.views.main import (
    ALL_VAR, ORDER_VAR, PAGE_VAR, SEARCH_VAR, IS_POPUP_VAR, TO_FIELD_VAR
)
# Additional changelist settings
LAYOUT_VAR = 's'
IGNORED_PARAMS = BASE_IGNORED_PARAMS + (LAYOUT_VAR, )

TREE_LAYOUT = 'tree'
LIST_LAYOUT = 'list'
ORDERED_DAG_SEQUENCE_FIELD_NAME = '_sequence'

class DagChangeList(ChangeList):
    def allow_node_drag(self, request):
        draggable = True
        for k,v in self.params.items():
            if k in [ALL_VAR, IS_POPUP_VAR, TO_FIELD_VAR, PAGE_VAR]:
                continue
            elif ORDER_VAR == k:
                if v is not '' and self.model.sequence_manager:  # Sorted nodes thefore disable is sort enabled
                    draggable = False
            elif SEARCH_VAR == k:
                if v is not '':
                    draggable = False  # disbaled moving nodes if filters are active
            elif LAYOUT_VAR == k:
                if v != TREE_LAYOUT:
                    draggable = False  # disable is not in tree view
            else:
                draggable = False
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
                order_type=''
            if base == ORDERED_DAG_SEQUENCE_FIELD_NAME:
                yield part
            else:
                yield "{}child__{}".format(order_type, base)

    def get_results_tree_relnode_extra(self, queryset):
        qs = self.queryset \
            .exclude(parent_questionedges__parent__in=queryset)
        if not qs.query.select_related:
            qs = self.apply_select_related(qs)
        if self.model.sequence_manager:
            qs = qs.annotate(**{ORDERED_DAG_SEQUENCE_FIELD_NAME: Value('a', output_field=TextField())})

        # Set ordering.
        ordering = list(self.get_ordering(request, qs,))
        qs = qs.order_by(*ordering)
        return qs

    def get_results_tree_extra(self, request, edge_queryset):
        ordering = list(self.get_ordering(request, self.queryset))
        name = self.model.get_edge_model()._meta.model_name
        def build_q(ref, value):
            return Q(**{ ref % {'name' : name}: value})

        def mod_query(qs):
            if not qs.query.select_related:
                qs = self.apply_select_related(qs)
            if self.model.sequence_manager:
                qs = qs.annotate(
                    **{
                        ORDERED_DAG_SEQUENCE_FIELD_NAME: Value(
                            'a', output_field=TextField())
                    })
            qs = qs.annotate(
                prime_parent= Coalesce(
                    Min('parents__id'),
                    Value(0, output_field=IntegerField()),
                    output_field=IntegerField()
                ),
            )
            return qs

        child_ids = list(edge_queryset.values_list('child_id',flat=True))
        nodes_ids = list(self.queryset.order_by().values_list('pk',flat=True))
        ditached_qs = mod_query(
            self.queryset \
                .filter(
                    ~Q(
                        build_q("parent_%(name)ss__parent_id__in", child_ids) |
                        build_q("parent_%(name)ss__isnull", True) |
                        Q(Q(parents__parents__isnull=True) & Q(parents__id__in=nodes_ids))
                    )
                ) \
            ).distinct() \
            .order_by()  #  Remove any order by as this is not allowed (postgres copes but not sqlite3 )
        root_qs = mod_query(
                self.queryset.filter(build_q("parent_%(name)ss__isnull",True))
            ) \
            .order_by()  #  Remove any order by as this is not allowed (postgres copes but not sqlite3 )
        qs = root_qs.union(ditached_qs)
        # Set ordering.
        qs = qs.order_by('prime_parent', *ordering)
        return qs

    def get_results_tree(self, request):
        qs = self.model.get_edge_model() \
            .objects \
            .filter(
                Q(child_id__in = self.queryset )
             ) \
            .annotate(
                siblings_count=Count('parent__children', distinct=True),
                is_child=Count('parent__parents'),
                children_count=Count('child__children', distinct=True),
                child_usage_count=Subquery(
                    self.model.get_node_model() \
                        .objects \
                        .filter(pk = OuterRef('child_id'))
                        .annotate(child_usage_count = Count('parents__pk'))
                        .values('child_usage_count')
                ),
                parent_used = Exists(self.queryset.filter(pk = OuterRef('parent_id')))
            )

        if not qs.query.select_related:
            qs = self.apply_select_related(qs, for_edge=True)

        if self.model.sequence_manager:
            order_component = self.model.sequence_manager \
                .get_edge_rel_sort_query_component(self.model, 'child', 'parent')
            qs = qs.annotate(**{ORDERED_DAG_SEQUENCE_FIELD_NAME:order_component})

        # Set ordering.
        ordering = list(self._convert_order_node_to_edge(self.get_ordering(request, qs,)))
        qs = qs.order_by(*ordering)
        return qs

    def get_results_list(self, request):
        qs = self.queryset \
            .annotate(
                children_count=Count('children', distinct=True),
                usage_count=Subquery(
                    self.model.get_node_model() \
                        .objects \
                        .filter(pk = OuterRef('id'))
                        .annotate(usage_count = Count('parents__pk'))
                        .values('usage_count')
                )
            )
        qs = self.apply_select_related(qs)

        if self.model.sequence_manager:
            order_component = self.model.sequence_manager \
                .get_node_rel_sort_query_component(self.model, 'child', 'parent')
            qs = qs.annotate(**{ORDERED_DAG_SEQUENCE_FIELD_NAME:order_component})

        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)
        return qs

    def get_results(self, request):
        self.result_list_extra = []
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

        if self.get_layout_style(request) != LIST_LAYOUT:
            self.result_list_extra = self.get_results_tree_extra(
                    request, result_list)
            result_count += len(self.result_list_extra)

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
        elif bool(self.model.sequence_manager):
            ordering = [ ORDERED_DAG_SEQUENCE_FIELD_NAME, ]
        return ordering

    def apply_select_related(self, qs, for_edge=False):
        if self.list_select_related is True:
            if for_edge:
                return qs.select_related()
            return qs.select_related()

        if self.list_select_related is False:
            if self.has_related_field_in_list_display():
                if for_edge:
                    return qs.select_related()
                return qs.select_related()

        if self.list_select_related:
            if for_edge:
                related = [ "child__{}".format(relation) for relation in self.list_select_related]
                return qs.select_related(*related)
            return qs.select_related(*self.list_select_related)
        return qs
