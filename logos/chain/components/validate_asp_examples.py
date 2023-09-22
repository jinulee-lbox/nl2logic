from typing import List

from clingo.ast import AST, ASTType

from nl2logic.logic_utils.pysolver.unify import unify
from nl2logic.logic_utils.pysolver.parse import parse_line

def validate_asp_list(asp_list: List, goal: AST):
    result = []
    for asp_dict in asp_list:
        asp: str = asp_dict["asp"].strip()
        
        # Heuristic. Check if asp code ends with a period
        if not asp.endswith("."):
            asp += "."
        
        # Heuristic. Check if asp is a rule, and head is a single literal
        try:
            parsed_asp = parse_line(asp)
        except:
            continue # Syntax error
        if parsed_asp.ast_type != ASTType.Rule:
            continue
        if parsed_asp.head.ast_type != ASTType.Literal:
            continue

        # Heuristic. Goal should unify with the goal to prove.
        if unify(goal, parsed_asp.head) is None:
            continue

        # If all satisfied, add to successful results.
        asp_dict["asp"] = asp
        result.append(asp_dict)
    return result