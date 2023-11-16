from typing import List, Tuple, Dict, Any
from copy import deepcopy, copy
import re
from clingo.ast import *

from .utils import flip_sign, is_negated, get_hash_head, parse_line
from .unify import unify, substitute
from .preprocess import preprocess

class ProofContext():
    def __init__(self):
        """A global context manager that runs through a proof.
        Stores current rules, variable re-indexing information, and more.

        Program contains a dictionary (JSON-compatible) of rules.
        Mandatory keys:
        - `asp` : contains a string version of the logic program.

        ex. [{'asp': 'a :- b, c(X).', 'comment': 'if b holds and c holds for any X, a holds.'}]
        """
        self.program: List[Dict[str, Any]] = []
        # Preprocess programs (add dual, split OR statements,...)
        self.preprocessed_program: List[AST] = []
        
        # Hashed dictionary for fast retrieval of rules
        self.rule_dict: Dict[str, List[AST]] = {}

        # Global index for rule instantiation.
        self.variable_index: int = 0

    def add_rule(self, line: Dict[str, Any]) -> None:
        self.program.append(line)
        
        # Parse string to AST
        rule = parse_line(line["asp"])
        assert "asp" in line
        
        # Add to preprocessed program list
        self.preprocessed_program.extend(preprocess(rule))
        
        # Add to rule dict (for fast finding)
        hash_head = get_hash_head(rule)
        if hash_head not in self.rule_dict:
            self.rule_dict[hash_head] = []
        
        # Check for duplicates
        is_dup = False
        # FIXME
        # for existing_rule in self.rule_dict[hash_head]:
        #     if unify(rule, existing_rule):
        #         is_dup = True
        if not is_dup:
            self.rule_dict[hash_head].append(rule)

    def find_rule(self, goal: AST):
        hash_head = get_hash_head(goal)
        if hash_head not in self.rule_dict:
            return []
        relevant_rules = self.rule_dict[hash_head]
        result = []
        for rule in relevant_rules:
            head = rule.head
            if unify(head, goal) is not None:
                result.append(deepcopy(rule))
        return result

    def reindex_variables(self, rule):
        rule_str = str(rule)
        # Re-index
        rule_str = re.sub(r"([,( ])(_*[A-Z][A-Za-z_0-9]*)(?=[,)]| [+\-*/%><=!])", f"\g<1>\g<2>_{self.variable_index}", rule_str) # attatch rule_idx to ordinary(non-anonymous) variables
        anonym_idx = 0
        while True:
            rule_str, replaced = re.subn(r"([,( ])_(?=[,)]| [+\-*/%><=!])", f"\g<1>_Anon_{self.variable_index}_{anonym_idx}", rule_str, count=1)
            if replaced == 0:
                break
            anonym_idx += 1
        self.variable_index += 1
        return parse_line(rule_str)

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