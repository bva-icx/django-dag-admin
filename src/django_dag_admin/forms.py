# -*- coding: utf-8 -*-
"""Forms for Django-Dag Models"""

from django import forms
from django.db.models import Count
from django.core.exceptions import ValidationError
from django.forms.models import ErrorList
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_dag_admin.utils import get_nodedepth


class BaseDagMoveForm(forms.ModelForm):
    @staticmethod
    def mk_indent(level):
        return '&nbsp;&nbsp;&nbsp;&nbsp;' * (level - 1)

    @classmethod
    def add_subtree(cls, for_node, node, options):
        """Recursively build options tree."""
        try:
            if for_node:
                node._meta.model.circular_checker(node, for_node)
        except ValidationError:
            # Catch ValidationError ie The object is an ancestor or it's self
            pass
        else:
            options.append(
                (node.pk,
                mark_safe(cls.mk_indent(get_nodedepth(node)) + escape(node))))
            for subnode in node.children.all():
                cls.add_subtree(for_node, subnode, options)

    @classmethod
    def mk_dropdown_tree(cls, model, for_node=None, for_edge=None):
        """Creates a tree-like list of choices"""
        options = [(0, _('-- root --'))]

        if for_node is None and for_edge:
            for_node = for_edge.child

        for node in model.objects.annotate(
                Count('parents')
        ).filter(parents__count=0):
            cls.add_subtree(for_node, node, options)
        return options


class MoveEdgeForm(BaseDagMoveForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None,
                 parent_object=None,
                 **kwargs):

        opts = self._meta
        if opts.model is None:
            raise ValueError('ModelForm has no model class specified')

        choices = None
        if choices is not None:
            lct = dict(self.base_fields['parent'].limit_choices_to)
            lct.update({'pk__in': [cc[0] for cc in choices]})
            self.base_fields['parent'].limit_choices_to = lct

        super().__init__(
            data=data, files=files, auto_id=auto_id, prefix=prefix,
            initial=initial, error_class=error_class,
            label_suffix=label_suffix, empty_permitted=empty_permitted,
            instance=instance, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        if parent is None:
            return cleaned_data
        try:
            child = cleaned_data['id'].child
        except AttributeError:
            return cleaned_data
        nodeModel = child._meta.model
        try:
            nodeModel._meta.model.circular_checker(parent, child)
        except ValidationError as err:
            self.add_error('parent', err)
        return cleaned_data


class MoveNodeForm(BaseDagMoveForm):
    pass
