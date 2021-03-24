# -*- coding: utf-8 -*-
import sys

import django
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.db.models import Min, Value as V
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError
from django.db.models import OuterRef, Subquery
from django.db.models import Count, F, Value

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_str

from django_dag.models.order_control import Position

try:
    from django.contrib.admin.options import TO_FIELD_VAR
except ImportError:
    from django.contrib.admin.views.main import TO_FIELD_VAR


class DjangoDagAdmin(admin.ModelAdmin):
    """Django Admin class for django-dag."""
    change_list_template = 'admin/django_dag_admin/change_list.html'
    show_attached_label = False
    show_detached_label = True

    def get_changelist(self, request, **kwargs):
        """
        Return the ChangeList class for use on the changelist page.
        """
        from django_dag_admin.views import DagChangeList
        return DagChangeList

    def get_changelist_instance(self, request):
        """
        Return a `ChangeList` instance based on `request`. May raise
        `IncorrectLookupParameters`.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        # Add the action checkboxes if any actions are available.
        if self.get_actions(request):
            list_display = ['action_checkbox', *list_display]
        sortable_by = self.get_sortable_by(request)
        ChangeList = self.get_changelist(request)
        return ChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            self.get_list_filter(request),
            self.date_hierarchy,
            self.get_search_fields(request),
            self.get_list_select_related(request),
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            sortable_by,
        )

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        if not hasattr(self, 'edges_admin'):
            return inline_instances

        for inline_class in self.edges_admin:
            inline = inline_class(self.model, self.admin_site)
            if request:
                inline_has_add_permission = inline._has_add_permission(request, obj)
                if not (inline.has_view_or_change_permission(request, obj) or
                        inline_has_add_permission or
                        inline.has_delete_permission(request, obj)):
                    continue
                if not inline_has_add_permission:
                    inline.max_num = 0
            inline_instances.append(inline)

        return inline_instances

    def get_urls(self):
        """
        Adds a url to move nodes to this admin
        """
        urls = super().get_urls()
        from django.views.i18n import JavaScriptCatalog

        jsi18n_url = url(r'^jsi18n/$',
            JavaScriptCatalog.as_view(packages=['django-dag-admin']),
            name='javascript-catalog'
        )
        new_urls = [
            url('^move/$', self.admin_site.admin_view(self.move_node), ),
            jsi18n_url,
        ]
        return new_urls + urls

    def get_node(self, node_id):
        return self.model.objects.get(pk=node_id)

    def get_edge(self, edge_id):
        if edge_id:
            return self.model.children.through.objects.get(pk=edge_id)
        return None

    def validate_move(self, node, target,):
        try:
            self.model.circular_checker(target, node)
        except ValidationError:
            return False
        return True

    def move_node(self, request):
        try:
            node_id = request.POST['node_id']
            sibling_id = request.POST['sibling_id']
            parent_id = request.POST['parent_id']
            edge_id = request.POST['edge_id']
            as_child = bool(int(request.POST.get('as_child', 0)))
            as_clone = bool(int(request.POST.get('as_clone', 0)))
        except (KeyError, ValueError):
            # Some parameters were missing return a BadRequest
            return HttpResponseBadRequest('Malformed POST params')

        node = self.get_node(node_id)
        target_id = sibling_id if as_child else parent_id
        target = self.get_node(target_id)
        edge = self.get_edge(edge_id)

        if bool(node.sequence_manager):
            if sibling_id and not as_child:
                parent = self.get_node(parent_id)
                sibling_before = self.get_node(sibling_id)
            else:
                sibling_before = target.get_last_child()

        try:
            if self.validate_move(node, target):
                if as_clone or edge is None:
                    if bool(node.sequence_manager):
                        newedge = target.insert_child_after(node, sibling_before)
                    else:
                        newedge = target.add_child(node)
                elif edge:
                    if bool(node.sequence_manager):
                        edge.child.move_node(
                            edge.parent, target, sibling_before,
                            position = Position.AFTER if sibling_before else Position.LAST)
                    else:
                        edge.child.move_node(edge.parent, target)
                else:
                    return HttpResponseBadRequest('Invalid move')
            else:
                return HttpResponseBadRequest('Invalid move')
        except Exception as err:
            return HttpResponseBadRequest('Exception raised during move')

        if as_child:
            msg = _('Moved node "%(node)s" as child of "%(other)s"')
        else:
            msg = _('Moved node "%(node)s" as sibling of "%(other)s"')
        messages.info(request, msg % {'node': node, 'other': target})
        return HttpResponse('OK')


def admin_factory(form_class):
    """
    Dynamically build a DjangoDagAdmin subclass for the given form class.
    :param form_class:
    :return: A DjangoDagAdmin subclass.
    """
    return type(
        form_class.__name__ + 'Admin',
        (DjangoDagAdmin,),
        dict(form=form_class))
