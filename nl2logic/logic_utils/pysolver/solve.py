from typing import List, Dict
from copy import deepcopy
import logging

from clingo.ast import *
from clingo.control import *
from clingo.symbol import *
from clingo.solving import *

from .utils import get_hash_head, is_negated, is_ground, flip_sign, NOT_EXIST, UNPROVED_YET
from .unify import unify
from .proof_state import ProofState

def update_proved_goal_table(proved_goal_table, stack, key, value):
    if key not in proved_goal_table:
        if value is None:
            proved_goal_table[key] = None
            return
        else:
            proved_goal_table[key] = [None]
    if key in proved_goal_table and proved_goal_table[key] is None:
        # Already certain that `key` cannot be proved
        # assert value is None
        if value is not None:
            raise ValueError(f"Goal {key} is marked as unprovable; however found a proof")
        return
    if proved_goal_table[key][0] is None:
        assert isinstance(value, ProofState)
        value_id = value.proved_substates
        # Proof is on progress
        if value_id not in [x.proved_substates for x in proved_goal_table[key][1:]]:
            proved_goal_table[key].append(value)

def consistency_check(rule_dict, proved_goal_table):
    if "#false" not in rule_dict:
        return True
    false_lit = rule_dict["#false"][0][0].head # [0](first rule)[0](rule itself) #cf. [*][1]: is_dual
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
    stack = [root]
    proofs = [] # List of completely proven states
    while len(stack) > 0:
        curr_state = stack.pop()
        # print(len(stack), curr_state.goal, curr_state.original_goal, curr_state.proved) #, curr_state.parent.goal if curr_state.parent else None)
        if curr_state.proved:
            update_proved_goal_table(proved_goal_table, stack, curr_state.goal, curr_state)
            if curr_state.parent is None:
                # Root literal has been proven
                proofs.append(curr_state)
                continue
            # Non-parent proof
            stack.append(curr_state.get_next_goal())
        else:
            solve_subgoal(curr_state, rule_dict, stack, proved_goal_table, unproved_callback)
    # print(f"End proof for {goal} : {len(proofs)} solutions")

    # Clean proved_goal_table
    for proof_list in proved_goal_table.values():
        if proof_list is not None and proof_list[0] is None:
            proof_list.pop(0)

    return proofs

def solve_subgoal(state: ProofState, rule_dict: Dict[str, List[AST]], stack: List[ProofState], proved_goal_table: Dict[AST, List[ProofState]], unproved_callback = None) -> None:
    # state: pointer to the current goal in the full proof
    goal = state.goal
    
    # Cached goals
    if goal in proved_goal_table: # At least one proof is found
        cached_states = proved_goal_table[goal]
        if cached_states is not None: # if None -> it is certain that it is not proven
            if cached_states[0] is not None: # if None -> more proofs to be found in the future
                # Goal has been proven more than once before
                # print(f"found {goal} in table, with {len(proved_goal_table[goal])} proofs")
                original_state = state
                visited = set() # Deduplicate grounded goals to prevent exponential state growth
                for cached_state in cached_states:
                    new_state = deepcopy(original_state)
                    # Bind underspecified goal to its proved version
                    bindings = unify(goal, cached_state.goal)
                    new_state.bind(bindings) # bindings is not None # because goal and cached_state.goal should unify
                    # Deduplicate grounded goals
                    if new_state.goal in visited:
                        continue
                    visited.add(new_state.goal)
                    # Mark the state as proved, and link to current proofs
                    new_state.proved = True
                    new_state.from_cache = True
                    stack.append(new_state)
                # Certain that all proofs are found
                return
        else:
            # Certain that cannot be proven
            return

    # Coinduction
    result_str = state.detect_loop()
    if result_str == "success": # even>=2 negation
        # Goal is grounded & already proved in state (coinduction success)
        # print("Coinduction success")
        state.proved = True
        stack.append(state)
        return
    elif result_str == "failure": # 0 or odd>=1 negations
        # Goal clashes with other proved goal (coinduction failure)
        # print("Coinduction failure")
        return
    else: # result == "none"
        # Neither coinduction success or failure
        pass

    # TODO Check grounded inequality / bool constants
    if goal.atom.ast_type == ASTType.Comparison:
        if not is_ground(goal):
            # raise ValueError("Comparison goal not grounded")
            return
        # Comparison
        lterm = goal.atom.term
        assert len(goal.atom.guards) == 1
        guard = goal.atom.guards[0] # Should be one and only, I guess
        op = guard.comparison
        rterm = guard.term
        if op == ComparisonOperator.Equal:
            # Equal : treat with `unify`
            bindings = unify(lterm, rterm)
            if bindings is not None:
                state = deepcopy(state)
                state.bind(bindings)
                state.proved = True # Bind two literals
                stack.append(state)
        elif op == ComparisonOperator.NotEqual:
            bindings = unify(lterm, rterm)
            if bindings is None:
                state.proved = True # Bind two literals
                stack.append(state)
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
                    stack.append(state)
        # Comparison clear!!
        return

    # print("[solve]", goal)
    # print(state.get_root())


    # If `not x` form, try to prove the dual form `x` first.
    if is_negated(goal):
        new_goal = deepcopy(state.goal)
        new_goal.sign = Sign.NoSign
        new_proved_states = solve(new_goal, rule_dict, initial_call=False, proved_goal_table=proved_goal_table, unproved_callback=unproved_callback)
        if len(new_proved_states) >= 1:
            # TODO add callback for trace failure
            # print(goal, "failed because", new_goal, "is proved")
            return
        else:
            # print(goal, "suceeded because", new_goal, "cannot be proved")
            pass

    
    # Head is plain literal(function, const, ..) -> Find relevant rules
    hash_head = get_hash_head(goal)
    relevant_rules = rule_dict.get(hash_head, [])
    # apply rules recursively
    original_state = state # preserve original state to prevent mix between rules
    is_any_rule_unified = False
    for rule, is_dual in relevant_rules:
        # Check if goal unifies with rule head, and get variable mapping
        head = deepcopy(rule.head)
        bindings = unify(goal, head)
        if bindings is None:
            continue # unification failure(rule head does not match current goal)

        state = deepcopy(original_state)
        # Mark state if it is proved by an implicit dual rule
        state.is_dual = is_dual

        is_any_rule_unified = True
        # Add binding information created by rules
        if len(rule.body) == 0:
            # fact, without rule body
            state.proved = True
            state.bind(bindings)
            stack.append(state)
        else: # len(rule.body) >= 1
            # Recursively apply the rules
            # Set new goal and register to current state
            new_rule_body = deepcopy(list(rule.body))
            new_goal = new_rule_body[0]
            new_state = ProofState(new_goal)
            new_state.parent = state
            if len(rule.body) > 1:
                new_state.goal_to_prove = new_rule_body[1:]
            else:
                new_state.goal_to_prove = []
            state.substate = new_state
            new_state.bind(bindings)
            # Append to stack
            stack.append(new_state)
    # Recover original state
    state = original_state
    
    # handle negation: if reach here, it is true
    if is_negated(goal) and not is_any_rule_unified:
        # not x
        # where x does not exists
        state.proved = True
        stack.append(state)
    
    # Track unproved goals by callback
    if unproved_callback is not None and not is_any_rule_unified:
        if not state.proved:
            # a goal is popped, but not proved nor inductively proceeded to subgoals
            unproved_callback(state.goal, UNPROVED_YET)
        elif state.proved and is_negated(state.goal):
            # `not x` is proved because `x` cannot be proved
            unproved_callback(flip_sign(state.goal), NOT_EXIST)