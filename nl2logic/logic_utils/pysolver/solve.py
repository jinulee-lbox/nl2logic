from typing import List, Dict
from copy import deepcopy
import logging

from clingo.ast import *
from clingo.control import *
from clingo.symbol import *
from clingo.solving import *

from .utils import get_hash_head, is_negated, is_ground, flip_sign, NOT_EXIST, UNPROVED_YET
from .unify import unify, substitute
from .proof_state import ProofState

def consistency_check(rule_dict, proved_goal_table):
    if "#false" not in rule_dict:
        return True
    false_lit = rule_dict["#false"][0].head # retrieve literal `#false`
    if solve(false_lit, rule_dict, initial_call=False, proved_goal_table=proved_goal_table):
        return False
    return True

def solve(goal: AST, rule_dict: Dict[str, List[AST]], proved_goal_table = None, initial_call=True, unproved_callback=None) -> List[ProofState]:
    # print(f"Start proof for {goal}")
    if proved_goal_table is None:
        proved_goal_table = dict()

    # Consistency check
    if initial_call and not consistency_check(rule_dict, proved_goal_table):
        return []
    
    # Depth-first search (with explicit state) for a vaild proof
    root = ProofState(deepcopy(goal))
    result = recursive_solve(root, rule_dict, proved_goal_table, unproved_callback)
    return result


def recursive_solve(state: ProofState, rule_dict: Dict[str, List[AST]], proved_goal_table: Dict[AST, List[ProofState]], unproved_callback = None) -> List[ProofState]:
    # state: pointer to the current goal in the full proof
    goal = state.goal
    
    ##### 1. Check cached goals #####
    if goal in proved_goal_table: # At least one proof is found
        cached_states = proved_goal_table[goal]
        if cached_states is None: # if None -> it is certain that it is not proven
            # print(f"found {goal} in table, cannot be proven")
            return []
        else:
            # Goal has been proven more than once before
            # print(f"found {goal} in table, with {len(proved_goal_table[goal])} proofs")
            return proved_goal_table[goal]

    ##### 2. Check coinduction (loop in proofs) #####
    result_str = state.detect_loop()
    if result_str == "success": # even>=2 negation
        # Goal is grounded & already proved in state (coinduction success)
        # print("Coinduction success")
        state.proved = True
        return [state]
    elif result_str == "failure": # 0 or odd>=1 negations
        # Goal clashes with other proved goal (coinduction failure)
        # print("Coinduction failure")
        return
    else: # result == "none"
        # Neither coinduction success or failure
        pass

    ##### 3. Check coinduction (loop in proofs) #####
    if goal.atom.ast_type == ASTType.Comparison:
        if not is_ground(goal):
            # Comparison goal not grounded -> fail to prove anything
            return []
        # Decompose comparison
        # (lterm) (guard (op) (rterm))
        lterm = goal.atom.term
        assert len(goal.atom.guards) == 1
        guard = goal.atom.guards[0]
        op = guard.comparison
        rterm = guard.term
        if op == ComparisonOperator.Equal:
            # Equal : treat with `unify`
            bindings = unify(lterm, rterm)
            if bindings is not None:
                state = deepcopy(state)
                state.bind(bindings)
                state.proved = True # Bind two literals
                return [state]
        elif op == ComparisonOperator.NotEqual:
            bindings = unify(lterm, rterm)
            if bindings is None:
                state.proved = True # Bind two literals
                return [state]
        else:
            # Greater/Less : only make sense if ground integers are compared
            # print(lterm.__class__, lterm.ast_type)
            lterm = lterm.symbol # Extract clingo.Symbol values
            rterm = rterm.symbol
            # Only compare numbers
            if not lterm.type == rterm.type == SymbolType.Number:
                raise ValueError(f"Non-integer literals ({lterm}, {rterm}) cannot be compared")
            if op == ComparisonOperator.GreaterThan and lterm.number > rterm.number or \
               op == ComparisonOperator.GreaterEqual and lterm.number >= rterm.number or \
               op == ComparisonOperator.LessThan and lterm.number < rterm.number or \
               op == ComparisonOperator.LessThan and lterm.number <= rterm.number:
                    state.proved = True
                    return [state]
        # Comparison clear!!

    ##### 4. Check classic negation (not x) #####
    if is_negated(goal):
        new_goal = deepcopy(state.goal)
        new_goal.sign = Sign.NoSign
        new_proved_states = recursive_solve(ProofState(new_goal), rule_dict, proved_goal_table, unproved_callback)
        if len(new_proved_states) >= 1:
            # TODO add callback for trace failure
            # print(goal, "failed because", new_goal, "is proved")
            return []
        else:
            # print(goal, "suceeded because", new_goal, "cannot be proved")
            pass

    ##### 5. Check rules and facts #####
    
    proved_states = [] # result list

    # Head is plain literal(function, const, ..) -> Find relevant rules
    hash_head = get_hash_head(goal)
    relevant_rules = rule_dict.get(hash_head, [])
    original_state = state # preserve original state to prevent mix between rules
    is_any_rule_unified = False

    # apply rules recursively
    for rule in relevant_rules:
        # Check if goal unifies with rule head, and get variable mapping
        bindings = unify(goal, rule.head)
        if bindings is None:
            continue # unification failure(rule head does not match current goal)
        else:
            is_any_rule_unified = True

        # State base to proof
        state = deepcopy(original_state)
        substitute(state.goal, bindings)

        # Add binding information created by rules
        if len(rule.body) == 0:
            # fact, without rule body
            state.add_proof([], rule)
            proved_states.append(state)
        else: # len(rule.body) >= 1
            # Recursively apply the rules
            # Set new goal and register to current state
            
            # Variable naming convention
            # target_state          subset  bodygoal  (not yet seen)
            # a               :-    b,      c,        d.
            # iter1. subset: [], bodygoal: b
            # iter2. subset: [b], bodygoal: c
            # iter3. subset: [b, c], bodygoal: d

            body_subset_proofs = [(state, [])]
            for i in range(len(rule.body)):
                bodygoal = deepcopy(rule.body[i])

                new_body_subset_proofs = []
                for target_state, subset_proof in body_subset_proofs:
                    curr_bodygoal = deepcopy(bodygoal)
                    # bind to current bindings
                    substitute(curr_bodygoal, bindings)
                    for subset_state in subset_proof:
                        substitute(curr_bodygoal, subset_state.bindings)
                    # Prove partially bound subgoals
                    new_state = ProofState(curr_bodygoal)
                    new_state_proofs = recursive_solve(new_state, rule_dict, proved_goal_table, unproved_callback)

                    # Extend subset (list of already proven goals) with fresh proved goal
                    for new_proof in new_state_proofs: # Each ProofStates contain single binding
                        # deepcopy to prevent crashing
                        new_target_state = deepcopy(target_state)
                        new_curr_proof = subset_proof + [new_proof] # Extend subset
                        new_body_subset_proofs.append((new_target_state, new_curr_proof))
                # update body_subset_proofs
                body_subset_proofs = new_body_subset_proofs
            
            for target_state, proof in body_subset_proofs:
                target_state.add_proof(proof, rule)
                proved_states.append(target_state)
                
    # Recover original state
    state = original_state
    
    # proved!
    if len(proved_states) > 0:
        state.proved = True
    # handle negation: if reach here, it is true
    if is_negated(goal) and not is_any_rule_unified:
        # not x
        # where x does not exists
        state.proved = True
        proved_states.append(state)

    ##### 6. Post-tasks: add to cache, failure callback #####

    # Cache update
    if state.proved:
        proved_goal_table[goal] = proved_states
    else:
        proved_goal_table[goal] = None

    # Track unproved goals by callback
    if unproved_callback is not None and not is_any_rule_unified:
        if not state.proved:
            # a goal is popped, but not proved nor inductively proceeded to subgoals
            unproved_callback(state.goal, UNPROVED_YET)
        elif state.proved and is_negated(state.goal):
            # `not x` is proved because `x` cannot be proved
            unproved_callback(flip_sign(state.goal), NOT_EXIST)

    return proved_states