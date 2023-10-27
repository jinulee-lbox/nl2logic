from typing import List, Tuple
from copy import deepcopy, copy
from clingo.ast import *
import pickle

from .utils import is_negated, flip_sign
from .unify import unify, substitute

class Stack():
    def __init__(self, goal: AST):
        assert goal.ast_type == ASTType.Literal
        self.goal = goal
        self.original_goal = deepcopy(goal) # Original goal before binding, for caching purpose
        self.proved = False
        self.parent: Stack = None
        # Children
        self.proved_substacks: List[Stack]= [] # proved
        self.substack: Stack = None # proving
        self.goal_to_prove: List[AST] = [] # will prove
        # Dual marker
        self.is_dual = False
        # Cache marker (if True, proved_substacks list is incomplete)
        self.from_cache = False

    def get_root(self):
        curr_stack = self
        while curr_stack.parent is not None:
            curr_stack = curr_stack.parent
        return curr_stack

    # TODO prevent infinite loops while proving
    def detect_loop(self) -> str:
        goal = self.goal
        loop_found = False
        positive_loop = False
        
        # Find loop in parents
        # Constraint Answer Set Programming Without Grounding - Appendix B
        curr_stack = self.parent
        while curr_stack is not None:
            # Found a loop
            if goal == curr_stack.goal:
                # FIXME strictly, return of unify() (bindings) should only contain var-var mapping
                loop_found = True
                positive_loop = True
                break
            elif goal == flip_sign(curr_stack.goal):
                # FIXME strictly, return of unify() (bindings) should only contain var-var mapping
                loop_found = True
                positive_loop = False
                break
            curr_stack = curr_stack.parent
        # Return result
        if loop_found:
            if positive_loop:
                return "success"
            else:
                return "failure"
        else:
            return "none"

    def bind(self, bindings):
        if len(bindings) == 0:
            # Time cutting -> empty binding does not need recursion
            return
        stack = self
        while stack is not None:
            # Replace variable to goal
            substitute(stack.goal, bindings)
            for sibling in stack.goal_to_prove:
                substitute(sibling, bindings)
            stack = stack.parent

    def __str__(self) -> str:
        return self._pprint(indent=0)
    def _pprint(self, indent: int) -> str:
        string = "  " * indent
        string += str(self.goal)
        string += "\n"
        # Proved subgoals
        for subgoal in self.proved_substacks:
            string += subgoal._pprint(indent+1)
        # Current subgoal
        if self.substack is not None:
            string += self.substack._pprint(indent+1)
        # Remaining goals
        if len(self.goal_to_prove) > 0:
            string += "  " * indent + "Remaining goals: "
            string += str([str(goal) for goal in self.goal_to_prove])
            string += "\n"
        return string
    
    def get_next_goal(self):
        assert self.proved
        curr_stack = deepcopy(self)

        # Update global constraints and proved literal cache
        # curr_stack.get_proved_goals().add(self.goal)

        parent = curr_stack.parent
        if parent is None:
            return curr_stack
        # Move proved goal into proven_substack
        parent.proved_substacks.append(curr_stack)
        # apply binding
        # curr_stack.bind(unify(self.original_goal, self.goal))
        if len(curr_stack.goal_to_prove) > 0:
            # Some portion of rule is proved -> move to next body literal
            next_goal = curr_stack.goal_to_prove[0]
            next_stack = Stack(next_goal)
            if len(curr_stack.goal_to_prove) > 1:
                next_stack.goal_to_prove = curr_stack.goal_to_prove[1:]
            else:
                next_stack.goal_to_prove = []
            parent.substack = next_stack
            next_stack.parent = parent
        else:
            # Last element of rule is proved -> parent is proved
            parent.proved = True
            # No subgoal to prove!
            curr_stack.parent.substack = None
            # Append to queue
            next_stack = parent
        
        # Detach parent for runtime efficiency
        curr_stack.parent = None
        # Remove goal_to_prove
        curr_stack.goal_to_prove = []
        return next_stack
    
    def find_goals_on_prove(self):
        # Find all goals that are currently being proved.
        # Goals are finally cached when it does not appear in this list for whole stack.
        curr = self.parent
        result = set()
        while curr is not None:
            if curr.proved:
                # Proved goals should not be searched
                break
            result.add(curr.goal)
            curr = curr.parent
        return result

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k in ["substack"]:
                continue
            elif k in ["proved_substacks"]:
                setattr(result, k, copy(v)) # Shallow copy for performance increase
            else:
                setattr(result, k, deepcopy(v, memo))
        return result