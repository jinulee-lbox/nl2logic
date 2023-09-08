from typing import List
from copy import deepcopy
import re
from collections import defaultdict

from clingo.ast import *
from clingo.control import *
from clingo.symbol import *

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
    def __init__(self, tree_str: str):
        self.root = None

        lines = tree_str.split("\n")
        stack = [] # List[Tuple[Node, int]]
        for line in lines[1:]: # remove `query` line
            # Determine level by leading whitespaces
            level = len(re.search("^\s*", line).group(0))
            line = line.strip()
            # Append to immediate parent
            while True:
                # Root node
                if len(stack) == 0:
                    self.root = JustificationTreeNode(line)
                    stack.append((self.root, level))
                    break
                # Found parent
                elif stack[-1][1] < level:
                    current = JustificationTreeNode(line)
                    stack[-1][0].add_child(current)
                    stack.append((current, level))
                    break
                if len(stack[-1][0].children) > 0:
                    stack[-1][0].group_finish()
                stack.pop()
        while len(stack) > 0:
            if len(stack[-1][0].children) > 0:
                stack[-1][0].group_finish()
            stack.pop()
    
    def __str__(self):
        return self.root._pprint([False], -1)

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

def remove_failed_answer_tree(tree):
    # Remove open-world semantics by following heuristic:
    # If a node children ends with `not (...∉...)` ,
    # it is assumed that it is an open world assumption.

    # a :- b(X).
    # b(x).
    # ?- not a.
    #    ㄴ not b(X ∉ [x])
    def remove_failed_answer_tree_(node: JustificationTreeNode) -> bool:
        # No children
        if len(node.children) == 0:
            return True
        # Check children and propagate False
        for child in node.children:
            if not remove_failed_answer_tree_(child):
                return False
        # Check last child
        last_child_repr = node.children[-1].repr
        if last_child_repr.startswith("not ") and "∉" in last_child_repr:
            return False
        return True
    return remove_failed_answer_tree_(tree.root)

def remove_proved(tree):
    # Simply peel off proved()
    def _remove_proved(node):
        for keyword in ["proved", "chs", "assume"]:
            if node.repr.startswith(keyword + "(") and node.repr.endswith(")"):
                node.repr = node.repr[len(keyword + "("):-len(")")]
    tree.transform(_remove_proved)

def remove_o_nmr_check(tree):
    # Two kinds of integrity: user-generated or automatically introduced.
    
    # Remove user-introduced constraints and add to main tree.
    # not o_chk_1
    # |_ e(x2)
    # |_ not b(x2)
    # not b(x2) :- e(x2) # we do not need to annotate positive constraints

    nmr_check = tree.find_node(["o_nmr_check"])
    repr_to_children_map = defaultdict(list)
    for nmr_constraint in nmr_check.children:
        for child in nmr_constraint.children:
            if child.repr.startswith('not '):
                new_node = JustificationTreeNode(child.repr)
                for new_child in nmr_constraint.children:
                    if new_child.repr != child.repr:
                        new_node.add_child(deepcopy(new_child))
                repr_to_children_map[child.repr].append(new_node.children)
    tree.root.remove_child("o_nmr_check")
    # Update original tree nodes
    def add_nmr_constraint_child(node: JustificationTreeNode):
        if node.repr in repr_to_children_map:
            for c in repr_to_children_map[node.repr]:
                for child in c:
                    node.add_child(child)
                node.group_finish()
    tree.transform(add_nmr_constraint_child)

def remove_unremoved_predicates(tree):
    def remove_unremoved_predicates_(node: JustificationTreeNode):
        # Remove o_* or not o_*
        def check_preserve(child):
            # s(CASP) internal predicates
            if child.repr.startswith("o_"):
                return False
            elif child.repr.startswith("not o_"):
                return False
            # \notin operator removed to ensure closed world semantics
            elif '∉' in child.repr:
                return False
            return True
        node.children = [child for child in node.children if check_preserve(child)]
    tree.transform(remove_unremoved_predicates_)

def remove_variables(tree):
    def remove_variables_(node):
        # variables = re.findall(r"[,(]([A-Z][0-9]*)(?=[,)])", node.repr)
        # for var in variables:
        #     node.repr = node.repr.replace(var, "_")
        node.repr = re.sub(r"([,(])([A-Z][0-9]*)(?=[,)])", "\g<1>_", node.repr)
    tree.transform(remove_variables_)

def remove_duplicates(tree):
    def remove_duplicates_(node):
        new_children = []
        new_group = []
        seen = set()
        for child, gid in zip(node.children, node._children_group):
            if gid < 0 or (child.repr, gid) not in seen:
                seen.add((child.repr, gid))
                new_children.append(child)
                new_group.append(gid)
        node.children = new_children
        node.group = new_group        
    tree.transform(remove_duplicates_)

def scasp_parse_just_trees(raw_output: str, debug=False):
    # Only leave justification tree
    answer_trees = [
        answer_set
        for answer_set in re.findall(r"% Justification\n(.*?\.)\n% Model", raw_output, re.DOTALL)
    ]

    # Data integrity check
    len_answer_sets = len([int(x) for x in re.findall("Answer ([0-9]+)", raw_output)])
    if len(answer_trees) != len_answer_sets:
        raise ValueError(f"Answer tree count({len(answer_trees)}) and answer set count({len_answer_sets}) does not match")

    # Remove auxiliary symbols: ∧, ←, ¬, .
    answer_trees = [
        tree.replace(" ∧", "").replace(" ←", "").replace("¬ ", "-").replace(".", "")
        for tree in answer_trees
    ]

    # Generate tree strcuture
    answer_trees = [
        JustificationTree(tree)
        for tree in answer_trees
    ]
    if debug:
        return answer_trees

    # Apply relevant transformation
    for tree in answer_trees:
        remove_proved(tree)

        # Check global constraints
        if tree.find_node(["o_nmr_check"]) is not None:
            remove_o_nmr_check(tree)

        remove_unremoved_predicates(tree) # remove o_* / ∉
        remove_variables(tree)
        remove_duplicates(tree)

    answer_trees = [tree for tree in answer_trees if remove_failed_answer_tree(tree)]

    return answer_trees

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
    # Recursive call
    for newchild in dest.children:
        recursive_list = []
        for node in node_list:
            for child in node.children:
                if child.repr == newchild.repr:
                    recursive_list.append(child)
                    break
        merge_just_tree_nodes(recursive_list, newchild)
    
    # Add tree-only nodes
    for node in node_list:
        added = False
        for child in node.children:
            if child.repr not in common_child_reprs:
                dest.add_child(child)
                common_child_reprs.add(child.repr)
                added = True
        if added:
            dest.group_finish()


def scasp_merge_just_trees(answer_trees):
    curr_nodes = [tree.root for tree in answer_trees]
    dummy_tree = JustificationTree("")
    dummy_tree.root = JustificationTreeNode(curr_nodes[0].repr)
    merge_just_tree_nodes(curr_nodes, dummy_tree.root)
    return dummy_tree