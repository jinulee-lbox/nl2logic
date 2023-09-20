from typing import *

from .parse import parse_program, parse_goal
from .solve import solve
from .justification_tree import *
from .utils import flip_sign
import logging

# DEBUG
from pyinstrument import Profiler

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
        proved=False
        tree = None
    return tree, proved
