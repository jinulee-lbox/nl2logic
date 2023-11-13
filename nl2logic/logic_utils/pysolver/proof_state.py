from typing import List, Tuple, Dict
from copy import deepcopy, copy
from clingo.ast import *

from .utils import flip_sign, is_negated
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
        negation_count = 0
        while curr_state is not None:
            if is_negated(curr_state.goal):
                negation_count += 1
            # Found a loop
            if unify(goal, curr_state.goal):
                loop_found = True
                break
            elif unify(goal, flip_sign(curr_state.goal)):
                loop_found = True
                break
            curr_state = curr_state.parent
        # Return result
        if loop_found:
            if negation_count > 0 and negation_count % 2 == 0:
                return "success"
            else:
                return "failure"
        else:
            return "none"

    def __str__(self) -> str:
        return self._pprint(indent=0)
    def _pprint(self, indent: int) -> str:
        string = "  " * indent
        string += f"{str(self.goal)} : {str(self.rule)}\n"
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