import itertools

from django.contrib import admin
from django_dag_admin.forms import MoveNodeForm
from django_dag_admin.admin import admin_factory


def register(admin_site, model):
    admin_class = admin_factory(MoveNodeForm)
    admin_site.register(model, admin_class)


def register_all(admin_site=admin.site):
    for model in itertools.chain():
        register(admin_site, model)
