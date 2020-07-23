"""
Templatetags for django-dag

These are to support the adding of drag and drop to the change list
"""

import datetime
import sys
from itertools import chain

import django
from django.db import models
from django.db.models import Q

from django.conf import settings
from django.contrib.admin.templatetags.admin_list import (
    result_headers, result_hidden_fields)
try:
    from django.contrib.admin.utils import (
        lookup_field, display_for_field, display_for_value)
except ImportError:  # < Django 1.8
    from django.contrib.admin.util import (
        lookup_field, display_for_field, display_for_value)
from django.core.exceptions import ObjectDoesNotExist
from django.template import Library
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.db.models import Min, Value as V
from django.db.models.functions import Coalesce

if sys.version < '3':
    import codecs

    def u(x):
        return codecs.unicode_escape_decode(x)[0]
else:
    def u(x):
        return x

register = Library()

if sys.version_info >= (3, 0):
    from django.utils.encoding import force_str
    from urllib.parse import urljoin
else:
    from django.utils.encoding import force_unicode as force_str
    from urlparse import urljoin


from django.utils.html import format_html

from django_dag_admin.templatetags import needs_checkboxes
from django_dag_admin.utils import get_nodedepth

def get_result_and_row_class(cl, field_name, result):
    if django.VERSION >= (1, 9):
        empty_value_display = cl.model_admin.get_empty_value_display()
    else:
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        empty_value_display = EMPTY_CHANGELIST_VALUE
    row_classes = ['field-%s' % field_name]
    try:
        f, attr, value = lookup_field(field_name, result, cl.model_admin)
    except ObjectDoesNotExist:
        result_repr = empty_value_display
    else:
        if django.VERSION >= (1, 9):
            empty_value_display = getattr(
                attr, 'empty_value_display', empty_value_display)
        if f is None:
            if field_name == 'action_checkbox':
                row_classes = ['action-checkbox']
            allow_tags = getattr(attr, 'allow_tags', False)
            boolean = getattr(attr, 'boolean', False)
            if django.VERSION >= (1, 9):
                result_repr = display_for_value(
                    value, empty_value_display, boolean)
            else:
                result_repr = display_for_value(value, boolean)
            # Strip HTML tags in the resulting text, except if the
            # function has an "allow_tags" attribute set to True.
            # WARNING: this will be deprecated in Django 2.0
            if allow_tags:
                result_repr = mark_safe(result_repr)
            if isinstance(value, (datetime.date, datetime.time)):
                row_classes.append('nowrap')
        else:
            related_field_name = 'rel' if django.VERSION <= (2, 0) else 'remote_field'
            if isinstance(getattr(f, related_field_name), models.ManyToOneRel):
                field_val = getattr(result, f.name)
                if field_val is None:
                    result_repr = empty_value_display
                else:
                    result_repr = field_val
            else:
                if django.VERSION >= (1, 9):
                    result_repr = display_for_field(
                        value, f, empty_value_display)
                else:
                    result_repr = display_for_field(value, f)
            if isinstance(f, (models.DateField, models.TimeField,
                              models.ForeignKey)):
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


def get_collapse(result):
    if result.children.count():
        collapse = ('<a href="#" title="" class="collapse expanded">'
                    '-</a>')
    else:
        collapse = '<span class="collapse">&nbsp;</span>'
    return collapse


def get_drag_handler(first):
    drag_handler = ''
    if first:
        drag_handler = ('<td class="drag-handler">'
                        '<span>&nbsp;</span></td>')
    return drag_handler


def items_for_result(cl, result, form, depth=None):
    """
    Generates the actual list of data.

    This has been shamelessly copied from original
    django.contrib.admin.templatetags.admin_list.items_for_result
    in order to alter the dispay for the first element
    """
    first = True
    pk = cl.lookup_opts.pk.attname
    for field_name in cl.list_display:
        result_repr, row_class = get_result_and_row_class(cl, field_name,
                                                          result)
        # If list_display_links not defined, add the link tag to the
        # first field
        if (first and not cl.list_display_links) or \
           field_name in cl.list_display_links:
            table_tag = {True: 'th', False: 'td'}[first]
            # This spacer indents the nodes based on their depth
            nodedepth  = get_nodedepth(result) if depth is None else depth
            spacer = get_spacer(first, nodedepth )

            # This shows a collapse or expand link for nodes with childs
            collapse = get_collapse(result)
            # Add a <td/> before the first col to show the drag handler
            drag_handler = get_drag_handler(first)
            first = False
            url = cl.url_for_result(result)
            # Convert the pk to something that can be used in Javascript.
            # Problem cases are long ints (23L) and non-ASCII strings.
            if cl.to_field:
                attr = str(cl.to_field)
            else:
                attr = pk
            value = result.serializable_value(attr)
            result_id = "'%s'" % force_str(value)
            onclickstr = (
                ' onclick="opener.dismissRelatedLookupPopup(window, %s);'
                ' return false;"')
            yield mark_safe(
                u('%s<%s%s>%s %s <a href="%s"%s>%s</a></%s>') % (
                    drag_handler, table_tag, row_class, spacer, collapse, url,
                    (cl.is_popup and onclickstr % result_id or ''),
                    conditional_escape(result_repr), table_tag))
        else:
            # By default the fields come from ModelAdmin.list_editable, but if
            # we pull the fields out of the form instead of list_editable
            # custom admins can provide fields on a per request basis
            if (
                    form and
                    field_name in form.fields and
                    not (
                        field_name == cl.model._meta.pk.name and
                        form[cl.model._meta.pk.name].is_hidden
                    )
            ):
                bf = form[field_name]
                result_repr = mark_safe(force_str(bf.errors) + force_str(bf))
            yield format_html(u('<td{0}>{1}</td>'), row_class, result_repr)
    if form and not form[cl.model._meta.pk.name].is_hidden:
        yield format_html(u('<td>{0}</td>'),
                          force_str(form[cl.model._meta.pk.name]))


def get_edge_id(parent, child):
    if all([parent, child]):
        edge = child.children.through.objects.get(
            child=child.pk, parent=parent.pk
        )
        return edge.pk if edge else None
    return None


def get_path_id(root_parts, leaf ):
    return '-'.join(map(
        lambda x:str(x.pk),
        chain(
            root_parts, [leaf]
        )))


def safe_getattr(obj, path):
    elements = path.split(".")
    while elements and obj is not None:
        obj = getattr(obj,elements.pop(0),None)
    return obj


def results(clst,request, pathparts=[]):
    process_start_id=0
    root=None
    if pathparts:
        root=pathparts[-1]
        process_start_id=root.pk

    depth = len(pathparts)
    if clst.formset:
        for res, form in zip(clst.result_list, clst.formset.forms):
            assert False
            yield (res.pk, process_start_id, depth,
                   res.children.count(), get_edge_id(root, res) or '',
                   get_path_id(pathparts,res),
                   list(items_for_result(clst, res, form, depth=depth)))
    else:
        results_list = clst.result_list
        ## If the paginator has slice our QS we can't filter it 
        #  any further, so we need to build an equivalent unsliced QS

        #
        # We look at the query to get the model_admin object for the current
        # page, and if we can't fnis that we use the DjangoAdmindefautl queryset
        #
        # The admin form queryset function adds ordering and annotations which
        # we use so we can't just use a new queryset on the model
        #

        if not results_list.query.can_filter():
            newslice = Q(pk__in = [ pk['pk'] for pk in results_list.values('pk')] )
            admin = safe_getattr(request,'resolver_match.func.model_admin')
            if admin:
                base_qs = admin.get_queryset(request)
            else:
                base_qs = (
                        results_list.model.objects
                            .annotate(_prime_parent=Coalesce(Min('_parents'), V(0)))
                            .order_by('-_prime_parent','pk')
                )

            results_list = base_qs.filter(pk__in = [ pk['pk'] for pk in results_list.values('pk')] )
        process_list=results_list.filter(
                Q(_prime_parent=process_start_id) | Q(_parents=(process_start_id,))
            ).distinct()

        ## If the list as already been paginated 
        for res in process_list:
            yield (res.pk, process_start_id, depth,
                   res.children.count(), get_edge_id(root, res) or '',
                   get_path_id(pathparts,res),
                   list(items_for_result(clst, res, None, depth=depth)))
            yield from results(clst, request, pathparts=pathparts+[res])


def check_empty_dict(GET_dict):
    """
    Returns True if the GET querstring contains on values, but it can contain
    empty keys.
    This is better than doing not bool(request.GET) as an empty key will return
    True
    """
    empty = True
    for k, v in GET_dict.items():
        # Don't disable on p(age) or 'all' GET param
        if v and k != 'p' and k != 'all':
            empty = False
    return empty


@register.inclusion_tag(
    'admin/django_dag_admin/change_list_results.html', takes_context=True)
def result_tree(context, cl, request):
    """
    Added 'filtered' param, so the template's js knows whether the results have
    been affected by a GET param or not. Only when the results are not filtered
    you can drag and sort the tree
    """

    # Here I'm adding an extra col on pos 2 for the drag handlers
    headers = list(result_headers(cl))
    headers.insert(1 if needs_checkboxes(context) else 0, {
        'text': '+',
        'sortable': True,
        'url': request.path,
        'tooltip': _('Return to ordered tree'),
        'class_attrib': mark_safe(' class="oder-grabber"')
    })
    return {
        'filtered': not check_empty_dict(request.GET),
        'result_hidden_fields': list(result_hidden_fields(cl)),
        'result_headers': headers,
        'results': list(results(cl, request)),
    }


def get_static_url():
    """Return a base static url, always ending with a /"""
    path = getattr(settings, 'STATIC_URL', None)
    if not path:
        path = getattr(settings, 'MEDIA_URL', None)
    if not path:
        path = '/'
    return path


@register.simple_tag
def django_dag_admin_css():
    """
    Template tag to print out the proper <link/> tag to include a custom .css
    """
    css_file = urljoin(get_static_url(), 'django-dag-admin/django-dag-admin.css')
    return format_html(
        """<link rel="stylesheet" type="text/css" href="{}"/>""",
        mark_safe(css_file)
    )


@register.simple_tag
def django_dag_admin_js():
    """
    Template tag to print out the proper <script/> tag to include a custom .js
    """
    path = get_static_url()
    js_file = urljoin(path, 'django-dag-admin/django-dag-admin.js')
    jquery_ui = urljoin(path, 'django-dag-admin/jquery-ui-1.8.5.custom.min.js')

    # Jquery UI is needed to call disableSelection() on drag and drop so
    # text selections arent marked while dragging a table row
    # http://www.lokkju.com/blog/archives/143
    TEMPLATE = (
        '<script type="text/javascript" src="{}"></script>'
        '<script>'
            '(function($){{jQuery = $.noConflict(true);}})(django.jQuery);'
        '</script>'
        '<script type="text/javascript" src="{}"></script>'
        )
    return format_html(
            TEMPLATE,
            mark_safe(js_file), mark_safe(jquery_ui)
        )
