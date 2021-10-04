# -*- coding: utf-8 -*-
# Additional node utilities


def get_nodedepth(node, root=None):
    """Return the node's depth"""
    if node.is_island() or node.is_root():
        return 0
    if root:
        roots = [root]
    else:
        roots = node.get_roots()
    return min(map(lambda x: x.distance(node), roots))
