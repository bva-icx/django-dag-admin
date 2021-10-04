from django.db import models

from django_dag.models import node_factory, edge_factory


class ConcreteNode(node_factory('ConcreteEdge')):
    """Test node, adds just one field"""
    name = models.CharField(max_length=32)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class ConcreteEdge(edge_factory(ConcreteNode, concrete=False)):
    """Test edge, adds just one field"""
    name = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):  # pragma: no cover
        return 'Edge %d' % self.pk
