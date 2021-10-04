from django.contrib import admin
from . import models


@admin.register(models.ConcreteNode)
class NodeAdmin(admin.ModelAdmin):
    fields = ('name', )


@admin.register(models.ConcreteEdge)
class EdgeAdmin(admin.ModelAdmin):
    fields = ('name', )
