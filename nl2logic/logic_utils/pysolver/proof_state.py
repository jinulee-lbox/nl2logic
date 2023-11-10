from typing import List, Tuple, Dict
from copy import deepcopy, copy
from clingo.ast import *

from .utils import flip_sign
from .unify import unify, substitute

class ProofState():
    def __init__(self, goal: AST):
        assert goal.ast_type == ASTType.Literal
        self.original_goal = goal
        self.proved = False
        self.parent: ProofState = None
        # Bindings
        self.goal = deepcopy(goal)
        self.bindings: Dict[AST, AST] = {}
        self.rule: AST = None
        self.is_dual: bool = None
        # Children
        self.proof: List[ProofState]= [] # proved

    def get_root(self):
        curr_state = self
        while curr_state.parent is not None:
            curr_state = curr_state.parent
        return curr_state

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

    def __str__(self) -> str:
        return self._pprint(indent=0)
    def _pprint(self, indent: int) -> str:
        string = "  " * indent
        string += f"{str(self.goal)}\n"
        # Proved subgoals
        for subgoal in self.proof:
            string += subgoal._pprint(indent+1)
        return string

    def add_proof(self, proof, rule):
        self.proved = True

        for p in proof:
            substitute(self.goal, p.bindings)
        self.bindings = unify(self.original_goal, self.goal)
        self.rule = rule

        # Co-link current state and subgoals
        self.proof = proof
        for subgoal_state in proof:
            subgoal_state.parent = self

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k in ["parent"]:
                setattr(result, k, copy(v)) # Shallow copy to prevent infinite recursion
            else:
                setattr(result, k, deepcopy(v, memo))
        return result