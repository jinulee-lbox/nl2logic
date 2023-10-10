from typing import List

from clingo.ast import AST, ASTType

from nl2logic.logic_utils.pysolver.unify import unify
from nl2logic.logic_utils.pysolver.parse import parse_line
from nl2logic.logic_utils.api import asp_parse_program, asp_extract_const_list
from nl2logic.database_utils.queries import db_find_missing_ontology

def validate_asp_list(asp_list: List, goal: AST):
    result = []
    for asp_dict in asp_list:
        if not isinstance(asp_dict, dict) or "asp" not in asp_dict or "comment" not in asp_dict:
            print("Wrong dict key")
            continue
        asp: str = asp_dict["asp"].strip()
        
        # Heuristic. Check if asp code ends with a period
        if not asp.endswith("."):
            asp += "."
        # Heuristic. Change single to double quote
        asp = asp.replace("'", '"')
        
        # Heuristic. Check if asp is a rule, and head is a single literal
        _, success = asp_parse_program([asp])
        success = success[0]["code"] == 0
        if not success:
            print("Syntax error")
            continue # Syntax error
        parsed_asp = parse_line(asp)
        if parsed_asp.ast_type != ASTType.Rule:
            print("Syntax error: Not rule")
            continue
        if parsed_asp.head.ast_type != ASTType.Literal:
            print("Syntax error: Head not literal")
            continue

        # Heuristic. Goal should unify with the goal to prove.
        if unify(goal, parsed_asp.head) is None:
            print("Generated head not unified to goal")
            continue

        const_list = asp_extract_const_list(asp, exclude_underscore=True)
        missing_ontology = db_find_missing_ontology(const_list)
        if len(missing_ontology) > 0: # missing ontology exists
            print("Missing ontology")
            continue

        # If all satisfied, add to successful results.
        asp_dict["asp"] = asp
        result.append(asp_dict)
    return result