from typing import List
from copy import deepcopy
import re
from collections import defaultdict

from clingo.ast import *
from clingo.control import *
from clingo.symbol import *
from .stack import Stack
from .utils import anonymize_vars

class JustificationTreeNode():
    def __init__(self, repr: str):
        self.repr = repr
        self.children = []
        self._children_group = []
        self._group = 1 # siblings with same group consist parent group
        self.parent = None
    
    def add_child(self, child, nongroup=False):
        self.children.append(child)
        if nongroup:
            self._children_group.append(-1)
        else:
            self._children_group.append(self._group)
        assert len(self.children) == len(self._children_group)

        child.parent = self
    
    def group_finish(self):
        self._group += 1

    def remove_child(self, repr):
        remove_ids = [
            i for i, c in enumerate(self.children) if c.repr == repr
        ]
        for remove_id in remove_ids:
            self.children.pop(remove_id)
            self._children_group.pop(remove_id)
            assert len(self.children) == len(self._children_group)
    
    def _pprint(self, continuous, group):
        # Set tree-formatted prefix
        prefix = ""
        for cont in continuous[:-1]:
            prefix += "│ " if cont else "  "
        if continuous[-1]:
            prefix += "├ "
        else:
            prefix += "└ "
        # If OR-conjunction is present, add group info
        if group >= 0:
            group_str = f"({group}) "
        else:
            group_str = ""
        # Print prefix
        pp = prefix + group_str + self.repr + "\n"
        is_multiple_groups = len(set(self._children_group)) > 1
        for i, (child, group) in enumerate(zip(self.children, self._children_group)):
            if i < len(self.children) - 1:
                pp += child._pprint(continuous + [True], group if is_multiple_groups else -1)
            else:
                pp += child._pprint(continuous + [False], group if is_multiple_groups else -1)
        return pp

    def _transform(self, function):
        # Postorder transformation
        for child in self.children:
            child._transform(function) # Propagate to children first to prevent infinite recursion
        function(self) # Transform myself

    def __str__(self):
        return self.repr
    def __repr__(self):
        return "`" + self.repr + "`"

class JustificationTree():
    def __init__(self, stack: Stack):
        if stack is None:
            # Empty tree
            return
        stack = stack.get_root()
        self.root = JustificationTreeNode(str(stack.goal))
        dfs = [(stack, self.root)]
        # preorder DFS on stack to traverse all nodes
        while len(dfs) > 0:
            curr, node = dfs.pop()
            # Visit children
            temp_dfs = []
            for substack in curr.proved_substacks:
                new_node = JustificationTreeNode(str(substack.goal))
                node.add_child(new_node)
                temp_dfs.append((substack, new_node))
            node.group_finish()
            dfs.extend(reversed(temp_dfs)) # reversed() to ensure first child appears first on the stack
    
    def __str__(self):
        result_str = self.root._pprint([False], -1)
        return anonymize_vars(result_str)

    def transform(self, function):
        self.root._transform(function)

    def find_node(self, node_seq):
        # Starts with first level(not root)
        node = self.root
        for node_rep in node_seq:
            new_node = None
            for child in node.children:
                if child.repr == node_rep:
                    new_node = child
            if new_node is not None:
                node = new_node
            else:
                # raise KeyError("Cannot find key " + node_rep + " in " + str(node_seq))
                return None
        return node

############################################################

def merge_just_tree_nodes(node_list: List[JustificationTreeNode], dest: JustificationTreeNode):
    # Merge tree2 into tree1.
    def get_child_repr_list(node):
        return [x.repr for x in node.children]
    child_repr_lists = map(get_child_repr_list, node_list)

    # Find all common representations..
    common_child_reprs = set.intersection(*[set(x) for x in child_repr_lists])
    # and add to dummy node
    first_node = node_list[0]
    for child in first_node.children:
        if child.repr in common_child_reprs:
            # Add to dummy node
            dest.add_child(JustificationTreeNode(child.repr), nongroup=True)

    # Add nodes that are not globally shared among merged trees
    for node in node_list:
        added = False
        for child in node.children:
            if child.repr not in common_child_reprs:
                dest.add_child(JustificationTreeNode(child.repr))
                common_child_reprs.add(child.repr)
                added = True
        if added:
            dest.group_finish()

    # Recursive call
    for newchild in dest.children:
        recursive_list = []
        for node in node_list:
            for child in node.children:
                if child.repr == newchild.repr:
                    recursive_list.append(child)
                    break
        merge_just_tree_nodes(recursive_list, newchild)


def merge_just_trees(answer_trees):
    curr_nodes = [tree.root for tree in answer_trees]
    dummy_tree = JustificationTree(stack=None)
    dummy_tree.root = JustificationTreeNode(curr_nodes[0].repr)
    merge_just_tree_nodes(curr_nodes, dummy_tree.root)
    return dummy_tree