import itertools

from django.contrib import admin
from django_test_admin.forms import movenodeform_factory
from django_test_admin.admin import admin_factory


def register(admin_site, model):
    form_class = movenodeform_factory(model)
    admin_class = admin_factory(form_class)
    admin_site.register(model, admin_class)


def register_all(admin_site=admin.site):
    for model in itertools.chain():
        register(admin_site, model)
