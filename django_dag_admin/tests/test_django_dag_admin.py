# -*- coding: utf-8 -*-
"""Unit/Functional tests"""

from django import VERSION as DJANGO_VERSION
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.views.main import ChangeList
#from django.contrib.auth.models import User, AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
#from django.db.models import Q
#from django.template import Template, Context
#from django.test import TestCase
#from django.test.client import RequestFactory
#import pytest

from django_dag_admin.admin import admin_factory, TO_FIELD_VAR
#from django_dag_admin.templatetags.admin_tree import get_static_url
from django_dag_admin.tests import models
from django_dag_admin.tests.admin import register_all as admin_register_all


admin_register_all()
