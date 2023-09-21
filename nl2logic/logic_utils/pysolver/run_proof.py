from typing import *

from .parse import parse_program, parse_goal
from .solve import solve
from .justification_tree import *
from .utils import flip_sign
import logging

# DEBUG
from pyinstrument import Profiler

# Markers for failed goals
NOT_EXIST = 0
USER_PROVED = 1

def get_proof_tree_from_preprocessed_program(preprocessed_program: str, conc_symbol: str, proved_goal_table: dict) -> Tuple[JustificationTree, bool]:
    logging.debug(f"?- {conc_symbol}.")
    # print(preprocessed_program)

    rule_table, _ = parse_program(preprocessed_program)
    goal = parse_goal(conc_symbol)
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
    # print(preprocessed_program)

    rule_table, _ = parse_program(preprocessed_program)
    goal = parse_goal(conc_symbol)
    # profiler = Profiler()
    # profiler.start()
    proofs = solve(goal, rule_table, proved_goal_table)

    # If proved, no goals are unproved
    if len(proofs) > 0:
        return []
    else:
        proved_goal_table[goal] = None # memoization for unproved root goal
        # Prove negated goal to find the reason
        proofs = solve(flip_sign(goal), rule_table, proved_goal_table)
        result = set()
        for stack in proofs:
            # Recurse down until hit floor / non-negated stack
            curr = stack.get_root()
            while True:
                if curr.is_dual:
                    # curr.goal is proved by a dual rule in this proof instance(Stack)
                    if len(curr.proved_substacks) > 0:
                        # Last body literal of dual rule is a flipped version of original rule,
                        # this is the cause for original proof failing
                        curr = curr.proved_substacks[-1]
                    else:
                        # Reached the bottom line
                        result.add((curr.goal, NOT_EXIST))
                        break
                else:
                    # curr.goal is proved by a user-defined rule
                    result.add((flip_sign(curr.goal), USER_PROVED))
                    # Recursive search??
                    break
    return list(result)