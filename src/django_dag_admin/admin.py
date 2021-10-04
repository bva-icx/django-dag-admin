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
from .actions import actions as dag_actions

try:
    from django.contrib.admin.options import TO_FIELD_VAR
except ImportError:
    from django.contrib.admin.views.main import TO_FIELD_VAR


class DjangoDagAdmin(admin.ModelAdmin):
    """Django Admin class for django-dag."""
    change_list_template = 'admin/django_dag_admin/change_list.html'
    show_attached_label = False
    show_detached_label = True

    def _get_base_actions(self):
        actions = list([
            [action_fn, action, action_text]
            for action_fn, action, action_text in super()._get_base_actions()
            if action != 'delete_selected'
        ])
        actions.extend(
            self.get_action(action) for action in dag_actions or []
        )
        return filter(None, actions)

    def get_queryset(self, request):
        qs=super().get_queryset(request)
        oqs = qs.with_sort_sequence()
        return oqs

    def get_object(self, request, object_id, from_field=None):
        """
        Return an instance matching the field and value provided, the primary
        key is used if no field is provided. Return ``None`` if no match is
        found or the object_id fails validation.
        """
        queryset = super().get_queryset(request, )
        model = queryset.model
        field = model._meta.pk if from_field is None else model._meta.get_field(from_field)
        try:
            object_id = field.to_python(object_id)
            return queryset.get(**{field.name: object_id})
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

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
        if node_id:
            return self.model.objects.get(pk=node_id)
        return None

    def get_edge(self, parent_id, child_id):
        if parent_id and child_id:
            return self.model.children.through.objects.filter(
                child_id=child_id,
                parent_id=parent_id
                ).first()
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
            node_parent_id = request.POST['node_parent_id']
            sibling_parent_id = request.POST['sibling_parent_id']
            as_child = bool(int(request.POST.get('as_child', 0)))
            as_clone = bool(int(request.POST.get('as_clone', 0)))
        except (KeyError, ValueError):
            # Some parameters were missing return a BadRequest
            return HttpResponseBadRequest('Malformed POST params')

        node = self.get_node(node_id)
        target_id = sibling_id if as_child else sibling_parent_id
        target = self.get_node(target_id)
        edge = self.get_edge(node_parent_id, node_id)

        if bool(node.sequence_manager):
            if sibling_id and not as_child:
                sibling_before = self.get_node(sibling_id)
            else:
                sibling_before = target.get_last_child()
        try:
            if target is None or self.validate_move(node, target):
                if target is None:
                    if node.parents.count() > 1:
                        messages.error(request, _('Node has too many parents'))
                        return HttpResponseBadRequest('Too many parents')
                    elif edge:
                        messages.info(request, _('Move node "%(node)s" to root' % {'node': node }))
                        edge.delete()
                        return HttpResponse('OK')
                    # No move needed
                    return HttpResponse('OK')
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
                    messages.error(request, _('Invalid move'))
                    return HttpResponseBadRequest('Invalid move')
            else:
                messages.error(request, _('Invalid topological move, causes circular node paths'))
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
