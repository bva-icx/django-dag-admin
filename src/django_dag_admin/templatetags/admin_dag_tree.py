"""
Templatetags for django-dag

These are to support the adding of drag and drop to the change list
"""

import datetime
import logging
from itertools import chain
from django.db import models
from django.contrib.admin.templatetags.admin_list import result_hidden_fields
from django.contrib.admin.templatetags.admin_list import (
    result_headers as base_result_headers
)
from django.contrib.admin.utils import (
    display_for_field,
    display_for_value,
    lookup_field,
)
from django.core.exceptions import ObjectDoesNotExist
from django.template import Library
from django.templatetags.static import static
from django.utils.encoding import force_str
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_dag_admin.views import LAYOUT_VAR, TREE_LAYOUT, LIST_LAYOUT
from django_dag_admin.templatetags import needs_checkboxes
from django_dag_admin.utils import get_nodedepth


register = Library()
logger = logging.getLogger(__name__)


def get_result_and_row_class(clist, field_name, result):
    empty_value_display = clist.model_admin.get_empty_value_display()
    row_classes = ['field-%s' % field_name]
    try:
        f, attr, value = lookup_field(field_name, result, clist.model_admin)
    except ObjectDoesNotExist:
        result_repr = empty_value_display
    else:
        empty_value_display = getattr(
            attr, 'empty_value_display', empty_value_display)
        if f is None:
            if field_name == 'action_checkbox':
                row_classes = ['action-checkbox']
            allow_tags = getattr(attr, 'allow_tags', False)
            boolean = getattr(attr, 'boolean', False)
            result_repr = display_for_value(value, empty_value_display, boolean)
            # Strip HTML tags in the resulting text, except if the
            # function has an "allow_tags" attribute set to True.
            # WARNING: this will be deprecated in Django 2.0
            if allow_tags:
                result_repr = mark_safe(result_repr)
            if isinstance(value, (datetime.date, datetime.time)):
                row_classes.append('nowrap')
        else:
            related_field_name = 'remote_field'
            if isinstance(getattr(f, related_field_name), models.ManyToOneRel):
                field_val = getattr(result, f.name)
                if field_val is None:
                    result_repr = empty_value_display
                else:
                    result_repr = field_val
            else:
                result_repr = display_for_field(value, f, empty_value_display)
            if isinstance(f, (models.DateField, models.TimeField, models.ForeignKey)):
                row_classes.append('nowrap')
        if force_str(result_repr) == '':
            result_repr = mark_safe('&nbsp;')
    row_class = mark_safe(' class="%s"' % ' '.join(row_classes))
    return result_repr, row_class


def get_spacer(first, depth):
    if first:
        spacer = '<span class="spacer">&nbsp;</span>' * (depth)
    else:
        spacer = ''
    return spacer


def get_collapse(result, has_children):
    if has_children:
        collapse = ('<a href="#" title="" class="collapse expanded">-</a>')
    else:
        collapse = '<span class="collapse">&nbsp;</span>'
    return collapse


def get_drag_handler(first):
    drag_handler = ''
    if first:
        drag_handler = ('<td class="drag-handler">'
                        '<span>&nbsp;</span></td>')
    return drag_handler


def get_detached_path_items(clist, upper_parent, node_path):
    for parent in upper_parent.ancestors:
        if str(parent.pk).rjust(4, '0') in node_path:
            for attr in ['pk']:
                value = parent.serializable_value(attr)
                result_id = "'%s'" % force_str(value)
                url = clist.url_for_result(parent)
                onclickstr = (
                    ' onclick="opener.dismissRelatedLookupPopup(window, %s);'
                    ' return false;"')
                yield mark_safe(
                    '<a href="%s"%s>%s</a>' % (
                        url,
                        (clist.is_popup and onclickstr % result_id or ''),
                        conditional_escape(force_str(value))
                    )
                )


def items_for_result(clist, result, form, depth=None, has_children=0):
    """
    Generates the actual list of data.

    This has been shamelessly copied from original
    django.contrib.admin.templatetags.admin_list.items_for_result
    in order to alter the dispay for the first element
    """
    first = True
    pk = clist.lookup_opts.pk.attname
    for field_name in clist.list_display:
        result_repr, row_class = get_result_and_row_class(clist, field_name,
                                                          result)
        # If list_display_links not defined, add the link tag to the
        # first field
        if (first and not clist.list_display_links) or \
           field_name in clist.list_display_links:
            table_tag = {True: 'th', False: 'td'}[first]
            # This spacer indents the nodes based on their depth
            nodedepth = get_nodedepth(result) if depth is None else depth
            spacer = get_spacer(first, nodedepth)

            # This shows a collapse or expand link for nodes with childs
            collapse = get_collapse(result, has_children)
            # Add a <td/> before the first col to show the drag handler
            drag_handler = get_drag_handler(first)
            first = False
            url = clist.url_for_result(result)
            # Convert the pk to something that can be used in Javascript.
            # Problem cases are long ints (23L) and non-ASCII strings.
            if clist.to_field:
                attr = str(clist.to_field)
            else:
                attr = pk
            value = result.serializable_value(attr)
            result_id = "'%s'" % force_str(value)
            onclickstr = (
                ' onclick="opener.dismissRelatedLookupPopup(window, %s);'
                ' return false;"')
            yield mark_safe(
                '%s<%s%s>%s %s <a href="%s"%s>%s</a></%s>' % (
                    drag_handler, table_tag, row_class, spacer, collapse, url,
                    (clist.is_popup and onclickstr % result_id or ''),
                    conditional_escape(result_repr), table_tag))
        else:
            # By default the fields come from ModelAdmin.list_editable, but if
            # we pull the fields out of the form instead of list_editable
            # custom admins can provide fields on a per request basis
            if (
                    form and
                    field_name in form.fields and
                    not (
                        field_name == clist.model._meta.pk.name and
                        form[clist.model._meta.pk.name].is_hidden
                    )
            ):
                bf = form[field_name]
                result_repr = mark_safe(force_str(bf.errors) + force_str(bf))
            yield format_html('<td{0}>{1}</td>', row_class, result_repr)
    if form and not form[clist.model._meta.pk.name].is_hidden:
        yield format_html('<td>{0}</td>',
                          force_str(form[clist.model._meta.pk.name]))


def get_path_id(root_parts, leaf):
    return '-'.join(map(
        lambda x: str(x.pk),
        chain(
            root_parts, [leaf]
        )))


def results(clst, request):
    yield None, None  # Fake entry to ensure list as started and can be split
    if clst.get_layout_style(request) == LIST_LAYOUT:
        yield from list_results(clst, request, clst.result_list)
    else:
        yield from tree_results(clst, request, clst.result_list)


def list_results(clst, request, result_list):
    if clst.formset:
        raise NotImplementedError("Dag Admin as formSet not supported")
    else:
        for res in result_list:
            yield (
                (
                    res.pk, '', '',
                    res.children_count, '', '',

                    list(
                        items_for_result(
                            clst, res, None,
                            depth=0,
                            has_children=bool(res.children),
                        )
                    )
                ),
                None
            )


def tree_results(clst, request, result_list):
    """
    For each row/item in the dag should yield a tuple of
        * node_id
        * parent_id
        * node_level
        * children_num
        * edge_id
        * path
        * result

    Some node will be yielded multiple times as the can be attached to multiple
    parent nodes
    """
    lastnode = None
    lastnode_detached = None
    lastnode_detached_path = []

    qs_pks = set(clst.get_results_tree(request).order_by().values_list('pk', flat=True))

    if clst.formset:
        raise NotImplementedError("Dag Admin as formSet not supported")
    else:
        for node in result_list:
            path = node.dag_node_path.split(',')
            depth = len(path) - 1
            row = [
                path[-1],
                path[-2] if depth else '',
                depth,
                node.children_count,
                node.parent_questionedge_set.filter(
                        parent__in=map(int, path)
                    ).values_list('pk', flat=True).first(
                ),
                node.dag_node_path.replace(',', '-'),
                list(
                    items_for_result(
                        clst, node, None,
                        depth=depth,
                        has_children=bool(node.children),
                    )
                )
            ]
            detached_path = get_detached_path(path, lastnode, qs_pks)
            force_attach = (lastnode is None and set(map(int, path)) <= qs_pks)
            next_detached = (lastnode_detached and (detached_path != []))
            lastnode_detached = (
                not force_attach and
                (
                    next_detached or
                    (len(path) > 1 and (lastnode is None or lastnode[0] != path[0]))
                )
            )
            if lastnode_detached:
                # Detached
                testlen = min(len(detached_path), len(lastnode_detached_path))
                newgroup = detached_path[:testlen] != lastnode_detached_path[:testlen]
                if testlen == 0 or newgroup:
                    row.append(get_detached_path_items(clst, node, detached_path))
                    lastnode_detached_path = detached_path
                else:
                    row.append(None)
                yield None, tuple(row)
            else:
                # Attached
                yield row, None
            lastnode = path


def get_detached_path(node_path, lastnode_path, qs_pks,):
    last_path = lastnode_path if lastnode_path else []
    rval = []
    for path_idx, pathpoint in enumerate(node_path):
        if not int(pathpoint) in qs_pks:
            rval.append(pathpoint)
        elif path_idx < len(last_path) and pathpoint == last_path[path_idx]:
            rval.append(pathpoint)
    return rval


def result_headers(context, clist, request):
    headers = list(base_result_headers(clist))
    style = clist.get_layout_style(request) or TREE_LAYOUT
    toggle_style = LIST_LAYOUT if style == TREE_LAYOUT else TREE_LAYOUT
    headers.insert(1 if needs_checkboxes(context) else 0, {
        "text": '+',
        "sortable": True,
        "sort_style": style,
        "url_primary": request.path,
        "url_toggle": clist.get_query_string({LAYOUT_VAR: toggle_style}),
        'tooltip': _('Return to dag'),
        'class_attrib': mark_safe(' class="oder-grabber"')
    })
    return headers


@register.inclusion_tag(
    'admin/django_dag_admin/change_list_results.html', takes_context=True)
def result_tree(context, clist, request):
    """
    Added 'filtered' param, so the template's js knows whether the results have
    been affected by a GET param or not. Only when the results are not filtered
    you can drag and sort the tree
    """
    attached, detached = list(zip(*list(results(clist, request))))
    return {
        'draggable': clist.allow_node_drag(request),
        'show_detached_label': clist.model_admin.show_detached_label,
        'show_attached_label': clist.model_admin.show_attached_label,
        'result_hidden_fields': list(result_hidden_fields(clist)),
        'result_headers': result_headers(context, clist, request),
        'results': {
            'attached': list(filter(lambda x: x is not None, attached)),
            'detached': list(filter(lambda x: x is not None, detached)),
        }
    }


@register.simple_tag
def django_dag_admin_css():
    """
    Template tag to print out the proper <link/> tag to include a custom .css
    """
    css_file = static('django-dag-admin/django-dag-admin.css')
    return format_html(
        """<link rel="stylesheet" type="text/css" href="{}"/>""",
        mark_safe(css_file)
    )


@register.simple_tag
def django_dag_admin_js():
    """
    Template tag to print out the proper <script/> tag to include a custom .js
    """
    js_file = static('django-dag-admin/django-dag-admin.js')
    jquery_ui = static('django-dag-admin/jquery-ui-1.8.5.custom.min.js')

    # Jquery UI is needed to call disableSelection() on drag and drop so
    # text selections arent marked while dragging a table row
    # http://www.lokkju.com/blog/archives/143
    TEMPLATE = (
        '<script type="text/javascript" src="{}"></script>'
        '<script>(function($){{jQuery = $.noConflict(true);}})(django.jQuery);</script>'
        '<script type="text/javascript" src="{}"></script>'
    )
    return format_html(
            TEMPLATE,
            mark_safe(js_file), mark_safe(jquery_ui)
        )
