from typing import List
from copy import deepcopy, copy
from clingo.ast import *

from .utils import flip_sign
from .unify import substitute

class ProofState():
    def __init__(self, goal: AST):
        assert goal.ast_type == ASTType.Literal
        self.goal = goal
        self.original_goal = deepcopy(goal) # Original goal before binding, for caching purpose
        self.proved = False
        self.parent: ProofState = None
        # Children
        self.proved_substates: List[ProofState]= [] # proved
        self.substate: ProofState = None # proving
        self.goal_to_prove: List[AST] = [] # will prove
        # Dual marker
        self.is_dual = False
        # Cache marker (if True, proved_substates list is incomplete)
        self.from_cache = False

    def get_root(self):
        curr_state = self
        while curr_state.parent is not None:
            curr_state = curr_state.parent
        return curr_state

    # TODO prevent infinite loops while proving
    def detect_loop(self) -> str:
        goal = self.goal
        loop_found = False
        positive_loop = False
        
        # Find loop in parents
        # Constraint Answer Set Programming Without Grounding - Appendix B
        curr_state = self.parent
        while curr_state is not None:
            # Found a loop
            if goal == curr_state.goal:
                # FIXME strictly, return of unify() (bindings) should only contain var-var mapping
                loop_found = True
                positive_loop = True
                break
            elif goal == flip_sign(curr_state.goal):
                # FIXME strictly, return of unify() (bindings) should only contain var-var mapping
                loop_found = True
                positive_loop = False
                break
            curr_state = curr_state.parent
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
        state = self
        while state is not None:
            # Replace variable to goal
            substitute(state.goal, bindings)
            for sibling in state.goal_to_prove:
                substitute(sibling, bindings)
            state = state.parent

    def __str__(self) -> str:
        return self._pprint(indent=0)
    def _pprint(self, indent: int) -> str:
        string = "  " * indent
        string += str(self.goal)
        string += "\n"
        # Proved subgoals
        for subgoal in self.proved_substates:
            string += subgoal._pprint(indent+1)
        # Current subgoal
        if self.substate is not None:
            string += self.substate._pprint(indent+1)
        # Remaining goals
        if len(self.goal_to_prove) > 0:
            string += "  " * indent + "Remaining goals: "
            string += str([str(goal) for goal in self.goal_to_prove])
            string += "\n"
        return string
    
    def get_next_goal(self):
        assert self.proved
        curr_state = deepcopy(self)

        # Update global constraints and proved literal cache
        # curr_state.get_proved_goals().add(self.goal)

        parent = curr_state.parent
        if parent is None:
            return curr_state
        # Move proved goal into proven_substate
        parent.proved_substates.append(curr_state)
        # apply binding
        # curr_state.bind(unify(self.original_goal, self.goal))
        if len(curr_state.goal_to_prove) > 0:
            # Some portion of rule is proved -> move to next body literal
            next_goal = curr_state.goal_to_prove[0]
            next_state = ProofState(next_goal)
            if len(curr_state.goal_to_prove) > 1:
                next_state.goal_to_prove = curr_state.goal_to_prove[1:]
            else:
                next_state.goal_to_prove = []
            parent.substate = next_state
            next_state.parent = parent
        else:
            # Last element of rule is proved -> parent is proved
            parent.proved = True
            # No subgoal to prove!
            curr_state.parent.substate = None
            # Append to queue
            next_state = parent
        
        # Detach parent for runtime efficiency
        curr_state.parent = None
        # Remove goal_to_prove
        curr_state.goal_to_prove = []
        return next_state
    
    def find_goals_on_prove(self):
        # Find all goals that are currently being proved.
        # Goals are finally cached when it does not appear in this list for whole state.
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
            if k in ["substate"]:
                continue
            elif k in ["proved_substates"]:
                setattr(result, k, copy(v)) # Shallow copy for performance increase
            else:
                setattr(result, k, deepcopy(v, memo))
        return result