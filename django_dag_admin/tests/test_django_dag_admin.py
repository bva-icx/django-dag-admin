# -*- coding: utf-8 -*-
"""Unit/Functional tests"""

from django import VERSION as DJANGO_VERSION
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.views.main import ChangeList
#from django.contrib.auth.models import User, AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
#from django.db.models import Q
#from django.template import Template, Context
from django.contrib.auth import get_user_model

from django.test import TestCase, Client
from django.test.client import RequestFactory


#from django_dag_admin.admin import admin_factory, TO_FIELD_VAR
#from django_dag_admin.templatetags.admin_tree import get_static_url
#from django_dag_admin.tests import models
from django_dag_admin.tests.admin import register_all as admin_register_all


admin_register_all()

class AdminTests(TestCase):
    def setUp(self,):
        # Create a super user.
        usermodel = get_user_model()
        self.u = usermodel.objects.create_user("Jim",'jim@example.com','password')
        self.u.is_superuser = True
        self.u.save()
        self.admin_client = Client()
        self.admin_client.force_login(self.u)

    def test_foo(self,):pass

    
