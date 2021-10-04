# -*- coding: utf-8 -*-
"""Unit/Functional tests"""

from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.templatetags.static import static
from .models import ConcreteNode


class AdminTests(TestCase):
    def setUp(self,):
        # Create a super user.
        usermodel = get_user_model()
        self.u = usermodel.objects.create_user(
            "Jim", 'jim@example.com', 'password')
        self.u.is_superuser = True
        self.u.is_staff = True
        self.u.save()
        self.admin_client = Client()
        self.admin_client.force_login(self.u)

    def test_edge_index_reachable(self,):
        url = reverse("admin:testapp_concreteedge_changelist")
        resp = self.admin_client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_node_index_reachable(self,):
        url = reverse("admin:testapp_concretenode_changelist")
        resp = self.admin_client.get(url, )
        self.assertEqual(resp.status_code, 200)

    def test_can_add_a_node(self,):
        url = reverse("admin:testapp_concretenode_add",)
        resp = self.admin_client.post(url, {'name': 'NodeX', '_save': 'save'})
        # After adding we are redirected to the index.
        self.assertEqual(resp.status_code, 302)

    def test_can_change_a_node(self,):
        origanal_node = ConcreteNode.objects.create(name='Node X')
        url = reverse("admin:testapp_concretenode_change", args=(origanal_node.pk,))
        new_name = 'Node Y'
        resp = self.admin_client.post(url, {'name': new_name, '_save': 'save'})
        # After adding we are redirected to the index.
        self.assertEqual(resp.status_code, 302)
        new_node = ConcreteNode.objects.get(pk=origanal_node.pk)
        self.assertEqual(new_node.name, new_name)


class TestAdminDagTemplateTags(TestCase):
    def test_dag_css(self):
        template = Template("{% load admin_list admin_dag_tree %}{% django_dag_admin_css %}")
        context = Context()
        rendered = template.render(context)
        expected = (
            '<link rel="stylesheet" type="text/css" '
            'href="' + static("django-dag-admin/django-dag-admin.css") + '"/>'
        )
        self.assertEqual(expected, rendered)

    def test_dag_js(self):
        template = Template("{% load admin_list admin_dag_tree %}{% django_dag_admin_js %}")
        context = Context()
        rendered = template.render(context)
        expected = (
            '<script type="text/javascript" '
            'src="' + static("django-dag-admin/django-dag-admin.js") + '"></script>'
            "<script>(function($){"
            "jQuery = $.noConflict(true);"
            "})(django.jQuery);</script>"
            '<script type="text/javascript" '
            'src="' + static("django-dag-admin/jquery-ui-1.8.5.custom.min.js") + '"></script>'
        )
        self.assertEqual(expected, rendered)
