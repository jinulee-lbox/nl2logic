from typing import *

from .parse import parse_program, parse_line
from .solve import solve
from .justification_tree import *
from .utils import flip_sign, is_negated
import logging

# Markers for failed goals
NOT_EXIST = 0
UNPROVED_YET = 1

def get_proof_tree_from_preprocessed_program(preprocessed_program: str, conc_symbol: str, proved_goal_table: dict) -> Tuple[JustificationTree, bool]:
    logging.debug(f"?- {conc_symbol}.")
    # print(preprocessed_program)

    rule_table, _ = parse_program(preprocessed_program)
    goal = parse_line(conc_symbol).head
    # profiler = Profiler()
    # profiler.start()
    proofs = solve(goal, rule_table, proved_goal_table)
    # profiler.stop()
    # profiler.print()

    # Parse and merge trees
    if len(proofs) > 0:
        just_trees = [JustificationTree(stack) for stack in proofs]
        merged_justtree = merge_just_trees(just_trees)
        proved=True
        tree = merged_justtree
    else:
        proved_goal_table[goal] = None # memoization for unproved root goal
        proved=False
        tree = None
        print([str(x[0]) for x in get_unproved_goals_from_preprocessed_program(preprocessed_program, conc_symbol, dict())])
    return tree, proved


def get_unproved_goals_from_preprocessed_program(preprocessed_program: str, conc_symbol: str, proved_goal_table: dict) -> List[AST]:
    logging.debug(f"?- {conc_symbol}.")
    result = set()
    # print(preprocessed_program)

    rule_table, _ = parse_program(preprocessed_program)
    goal = parse_line(conc_symbol).head

    proofs = solve(goal, rule_table, proved_goal_table)
    # Find `not ...` goals that are not yet proved
    for stack in proofs:
        # Recurse down until hit floor / non-negated stack
        provestack = [stack.get_root()]
        while len(provestack) > 0:
            curr = provestack.pop()
            if len(curr.proved_substacks) > 0:
                # Exhaustive search for all substacks
                provestack.extend(curr.proved_substacks)
            elif is_negated(curr.goal):
                # If encounter a dual rule
                result.add((flip_sign(curr.goal), NOT_EXIST))

    # Negated goals for dual rules
    proved_goal_table[goal] = None # memoization for unproved root goal
    # Prove negated goal to find the reason
    proofs = solve(flip_sign(goal), rule_table, proved_goal_table)
    for stack in proofs:
        # Recurse down until hit floor / non-negated stack
        provestack = [stack.get_root()]
        while len(provestack) > 0:
            curr = provestack.pop()
            if len(curr.proved_substacks) > 0:
                # Last body literal of dual rule is a flipped version of original rule,
                # this is the cause for original proof failing
                provestack.extend(curr.proved_substacks)
                # Remove trivial proofs for `not x` (auto True because its dual cannot be proved)
                result.discard((flip_sign(curr.goal), UNPROVED_YET))
            elif is_negated(curr.goal):
                result.add((flip_sign(curr.goal), UNPROVED_YET))

    return list(result)