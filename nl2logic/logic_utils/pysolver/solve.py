from typing import List, Dict
from copy import deepcopy
import logging

from clingo.ast import *
from clingo.control import *
from clingo.symbol import *
from clingo.solving import *

from .utils import get_hash_head, is_negated, is_ground
from .unify import unify
from .stack import Stack

def update_proved_goal_table(proved_goal_table, queue, key, value):
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
        assert isinstance(value, Stack)
        value_id = value.proved_substacks
        # Proof is on progress
        if value_id not in [x.proved_substacks for x in proved_goal_table[key][1:]]:
            proved_goal_table[key].append(value)

def consistency_check(rule_dict, proved_goal_table):
    if "#false" not in rule_dict:
        return True
    false_lit = rule_dict["#false"][0][0].head # [0](first rule)[0](rule itself) #cf. [*][1]: is_dual
    if solve(false_lit, rule_dict, initial_call=False, proved_goal_table=proved_goal_table):
        return False
    return True

def solve(goal: AST, rule_dict: Dict[str, List[AST]], proved_goal_table = None, initial_call=True) -> List[Stack]:
    # print(f"Start proof for {goal}")
    if proved_goal_table is None:
        proved_goal_table = dict()

    # Consistency check
    if initial_call and not consistency_check(rule_dict, proved_goal_table):
        return []
    
    # Depth-first search (with explicit stack) for a vaild proof
    root = Stack(deepcopy(goal))
    queue = [root]
    proofs = [] # List of completely proven stacks
    while len(queue) > 0:
        curr_stack = queue.pop()
        # print(len(queue), curr_stack.goal, curr_stack.proved) #, curr_stack.parent.goal if curr_stack.parent else None)
        if curr_stack.proved:
            update_proved_goal_table(proved_goal_table, queue, curr_stack.original_goal, curr_stack)
            if curr_stack.parent is None:
                # Root literal has been proven
                proofs.append(curr_stack)
                continue
            # Non-parent proof
            queue.append(curr_stack.get_next_goal())
        else:
            _solve(curr_stack, rule_dict, queue, proved_goal_table)
    # print(f"End proof for {goal} : {len(proofs)} solutions")

    # Clean proved_goal_table
    for proof_list in proved_goal_table.values():
        if proof_list is not None and proof_list[0] is None:
            proof_list.pop(0)

    return proofs

def _solve(stack: Stack, rule_dict: Dict[str, List[AST]], queue: List[Stack], proved_goal_table: Dict[AST, List[Stack]]) -> None:
    # stack: pointer to the current goal in the full proof
    goal = stack.goal
    
    # Cached goals
    if goal in proved_goal_table: # At least one proof is found
        cached_stacks = proved_goal_table[goal]
        if cached_stacks is not None: # if None -> it is certain that it is not proven
            if cached_stacks[0] is not None: # if None -> more proofs to be found in the future
                # Goal has been proven more than once before
                # print(f"found {goal} in table, with {len(proved_goal_table[goal])} proofs")
                original_stack = stack
                for cached_stack in cached_stacks:
                    new_stack = deepcopy(original_stack)
                    # Bind underspecified goal to its proved version
                    bindings = unify(goal, cached_stack.goal)
                    new_stack.bind(bindings) # bindings is not None # because goal and cached_stack.goal should unify
                    # Mark the stack as proved, and link to current proofs
                    new_stack.proved = True
                    new_stack.proved_substacks = cached_stack.proved_substacks
                    # Add to stack as proved goal (will be immediately popped)
                    queue.append(new_stack)
                # Certain that all proofs are found
                return
        else:
            # Certain that cannot be proven
            return

    # Coinduction
    result_str = stack.detect_loop()
    if result_str == "success": # even>=2 negation
        # Goal is grounded & already proved in stack (coinduction success)
        # print("Coinduction success")
        stack.proved = True
        queue.append(stack)
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
            raise ValueError("Comparison goal not grounded")
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
                stack = deepcopy(stack)
                stack.bind(bindings)
                stack.proved = True # Bind two literals
                queue.append(stack)
        elif op == ComparisonOperator.NotEqual:
            bindings = unify(lterm, rterm)
            if bindings is None:
                stack.proved = True # Bind two literals
                queue.append(stack)
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
                    stack.proved = True
                    queue.append(stack)
        # Comparison clear!!
        return

    # print("[solve]", goal)
    # print(stack.get_root())


    # If `not x` form, try to prove the dual form `x` first.
    if is_negated(goal):
        new_goal = deepcopy(stack.goal)
        new_goal.sign = Sign.NoSign
        new_proved_stacks = solve(new_goal, rule_dict, initial_call=False, proved_goal_table=proved_goal_table)
        if len(new_proved_stacks) >= 1:
            # TODO add callback for trace failure
            # print(goal, "failed because", new_goal, "is proved")
            return
        else:
            # Cannot prove the positive dual
            stack.proved = True
            # print(goal, "suceeded because", new_goal, "cannot be proved")
            pass

    
    # Head is plain literal(function, const, ..) -> Find relevant rules
    hash_head = get_hash_head(goal)
    relevant_rules = rule_dict.get(hash_head, [])
    # apply rules recursively
    original_stack = stack # preserve original stack to prevent mix between rules
    is_any_rule_unified = False
    for rule, is_dual in relevant_rules:
        # Check if goal unifies with rule head, and get variable mapping
        head = deepcopy(rule.head)
        bindings = unify(goal, head)
        if bindings is None:
            continue # unification failure(rule head does not match current goal)

        stack = deepcopy(original_stack)
        # Mark stack if it is proved by an implicit dual rule
        stack.is_dual = is_dual

        is_any_rule_unified = True
        # Add binding information created by rules
        if len(rule.body) == 0:
            # fact, without rule body
            stack.proved = True
            stack.bind(bindings)
            queue.append(stack)
        else: # len(rule.body) >= 1
            # Recursively apply the rules
            # Set new goal and register to current stack
            new_rule_body = deepcopy(list(rule.body))
            new_goal = new_rule_body[0]
            new_stack = Stack(new_goal)
            new_stack.parent = stack
            if len(rule.body) > 1:
                new_stack.goal_to_prove = new_rule_body[1:]
            else:
                new_stack.goal_to_prove = []
            stack.substack = new_stack
            new_stack.bind(bindings)
            # Append to queue
            queue.append(new_stack)
    
    # handle negation: if reach here, it is true
    if is_negated(goal):
        # not x
        # where x does not exists
        stack.proved = True
        queue.append(stack)