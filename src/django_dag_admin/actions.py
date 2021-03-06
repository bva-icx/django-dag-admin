from itertools import chain
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy
from django.urls import reverse


def show_decendants(model_admin, request, queryset):
    """
    Add filter to limit the day the the selected descendants
    """
    def process(node):
        return node.get_descendant_pks() + [node.pk]
    return _do_select(model_admin, request, queryset, process)
show_decendants.short_description = gettext_lazy(  # noqa: E305
    "Show descendants of nodes")


def show_ancestors(model_admin, request, queryset):
    """
    Add filter to limit the node
    """
    def process(node):
        return node.get_ancestor_pks() + [node.pk]

    return _do_select(model_admin, request, queryset, process)
show_ancestors.short_description = gettext_lazy(  # noqa: E305
    "Show ancestors of nodes")


def show_root_to_leaf_through(model_admin, request, queryset):
    """
    Add filter to limit the node
    """
    def process(node):
        return node.get_clan_pks()
    return _do_select(model_admin, request, queryset, process)
show_root_to_leaf_through.short_description = gettext_lazy(  # noqa: E305
    "Show clan of nodes")


def _do_select(model_admin, request, queryset, fn):
    clst = model_admin.get_changelist_instance(request)
    model = model_admin.model
    opts = model._meta
    urlparams = clst.get_query_string({
        'pk__in': ','.join(
            set(map(
                str,
                chain(
                    *map(
                        fn,
                        queryset.order_by().all()
                    )
                )
            ))
        )
    })
    post_url = reverse('admin:%s_%s_changelist' %
                    (opts.app_label, opts.model_name),
                    current_app=model_admin.admin_site.name
                )
    return HttpResponseRedirect(post_url + urlparams)


actions = (
    show_decendants,
    show_ancestors,
    show_root_to_leaf_through,
)
