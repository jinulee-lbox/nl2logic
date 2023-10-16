from typing import List, Dict
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
    def __init__(self, proofs: List[Stack], proved_goal_table: Dict[AST, List[Stack]]):
        if proofs is None:
            # Empty tree list
            return

        self.root = JustificationTreeNode("")
        init_proofs = [stack.get_root() for stack in proofs]
        bfs = [(init_proofs, self.root)]
        # bfs on stack to traverse all nodes
        while len(bfs) > 0:
            proofs, parent_node = bfs.pop(0)
            # Group proofs by original_goal (i.e. rules that directly generate the fact)
            unique_goals = defaultdict(list)
            for stack in proofs:
                unique_goals[stack.goal].append(stack)

            for key, value in unique_goals.items():
                # Add a unique child node
                node = JustificationTreeNode(str(key))
                parent_node.add_child(node)

                # Collect subgoals
                unique_subgoals = defaultdict(list)
                for stack in value:
                    # Expand proof stacks if they are from_cache
                    if stack.from_cache:
                        print(stack.goal, stack.original_goal, len(proved_goal_table[stack.original_goal]))
                        # They do not have valid proved_substacks;
                        # Retrieve from cache
                        if proved_goal_table is not None:
                            for instance in proved_goal_table[stack.original_goal]:
                                for subgoal in instance.proved_substacks:
                                    unique_subgoals[subgoal.goal].append(subgoal)
                    else:
                        for subgoal in stack.proved_substacks:
                            unique_subgoals[subgoal.goal].append(subgoal)
                
                for subkey, subvalue in unique_subgoals.items():
                    bfs.append((subvalue, node))
        
        if len(self.root.children) == 1:
            self.root = self.root.children[0]
    
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
