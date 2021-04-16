import itertools

from django.contrib import admin
from django_dag_admin.forms import MoveNodeForm
from . import models
from django.db.models import Model

from django_dag_admin.formset import DjangoDagAdminFormSet
from django_dag_admin.admin import DjangoDagAdmin


@admin.register(models.ConcreteNode)
class NodeAdmin(admin.ModelAdmin):
    fields = ('name', )

@admin.register(models.ConcreteEdge)
class EdgeAdmin(admin.ModelAdmin):
    fields = ('name', )


