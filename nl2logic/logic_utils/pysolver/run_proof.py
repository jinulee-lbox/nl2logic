from typing import *

from .parse import parse_program
from .utils import parse_line
from .solve import solve
from .proof_state import ProofContext
from .justification_tree import *
import logging

def get_proof_tree(program: List[Dict[str, Any]], goal: AST) -> JustificationTree:
    logging.debug(f"?- {str(goal)}.")

    context = ProofContext()
    for line in program:
        context.add_rule(line)

    proofs = solve(goal, context)

    # Parse and merge trees
    if len(proofs) > 0:
        tree = JustificationTree(proofs)
    else:
        tree = None
        # print([str(x) for x in get_unproved_goals(preprocessed_program, conc_symbol, dict())])
    return tree


def get_unproved_goals(preprocessed_program: str, conc_symbol: str) -> List[AST]:
    logging.debug(f"?- {conc_symbol}.")
    result = []
    # print(preprocessed_program)

    rule_table, _ = parse_program(preprocessed_program)
    goal = parse_line(conc_symbol).head

    proofs = solve(goal, rule_table, unproved_callback=lambda x,y : result.append((x, y)))
    return result

if __name__ == "__main__":
    from .utils import unproved_goal_state_to_str

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
    result = get_proof_tree(program, parse_line("not fin(_).").head)
    print(result)
    # result = get_unproved_goals(program, "not fin(_).", {})
    # print([(str(x[0]), unproved_goal_state_to_str(x[1])) for x in result])