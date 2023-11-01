from typing import *

from .parse import parse_program, parse_line
from .solve import solve
from .justification_tree import *
from .utils import flip_sign, is_negated, NOT_EXIST, UNPROVED_YET
import logging

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
        tree = JustificationTree(proofs, proved_goal_table)
        proved=True
    else:
        proved_goal_table[goal] = None # memoization for unproved root goal
        proved=False
        tree = None
        # print([str(x) for x in get_unproved_goals_from_preprocessed_program(preprocessed_program, conc_symbol, dict())])
    return tree, proved


def get_unproved_goals_from_preprocessed_program(preprocessed_program: str, conc_symbol: str, proved_goal_table: dict) -> List[AST]:
    logging.debug(f"?- {conc_symbol}.")
    result = set()
    # print(preprocessed_program)

    rule_table, _ = parse_program(preprocessed_program)
    goal = parse_line(conc_symbol).head

    proofs, unproved_goals = solve(goal, rule_table, proved_goal_table, get_unproved_goals=True, initial_call=False, unproved_goals=list())
    if len(proofs) > 0:
        # Given goal is proved
        # -> change status to not exist
        # unproved_goals = [(x[0], NOT_EXIST) for x in unproved_goals]
        pass
    return unproved_goals

if __name__ == "__main__":

    program = """fin(X) :- not a(X).
not fin(X) :- a(X).
a(X) :- z(X), not b(X, _).
not a(X) :- not z(X).
not a(X) :- z(X), b(X, _).
b(X, 1) :- c(X).
not b(X, 1) :- not c(X).
b(X, 2) :- d(X).
not b(X, 2) :- not d(X).
z(k).
"""
    result = get_unproved_goals_from_preprocessed_program(program, "fin(k).", dict())
    print([str(x[0]) for x in result])