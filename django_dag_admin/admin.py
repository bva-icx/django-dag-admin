# -*- coding: utf-8 -*-
import sys

import django
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.db.models import Min, Value as V
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_str


try:
    from django.contrib.admin.options import TO_FIELD_VAR
except ImportError:
    from django.contrib.admin.views.main import TO_FIELD_VAR


class DjangoDagAdmin(admin.ModelAdmin):
    """Django Admin class for django-dag."""
    change_list_template = 'admin/django_dag_admin/change_list.html'
    order_by = ('-_prime_parent','pk')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _prime_parent=Coalesce(Min('_parents'), V(0))
        ).order_by(*self.order_by)

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

    def validate_move(self, node, target, edge=None):
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
        except (KeyError, ValueError):
            # Some parameters were missing return a BadRequest
            return HttpResponseBadRequest('Malformed POST params')

        node = self.get_node(node_id)
        target_id = sibling_id if as_child else parent_id
        target = self.get_node(target_id)
        edge = self.get_edge(edge_id)

        try:
            if self.validate_move(node, target, edge):
                if edge:
                    edge.parent=target
                    edge.save()
                else:
                    target.add_child(node)
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
