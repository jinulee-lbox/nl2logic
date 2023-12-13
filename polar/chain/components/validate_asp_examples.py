from typing import List

from clingo.ast import AST, ASTType

from pysolver.unify import find_bindings
from pysolver.utils import parse_line
from nl2logic.logic_utils import asp_parse_program, asp_extract_const_list

def validate_asp_list(asp_list: List, goal: AST, polar_context):
    result = []
    error = []
    for asp_dict in asp_list:
        if not isinstance(asp_dict, dict) or "asp" not in asp_dict or "comment" not in asp_dict:
            error.append("Wrong dict key")
            continue
        asp: str = asp_dict["asp"].strip()
        
        # Heuristic. Check if asp code ends with a period
        if not asp.endswith("."):
            asp += "."
        # Heuristic. Change single to double quote
        asp = asp.replace("'", '"')
        asp_dict['asp'] = asp
        
        # Heuristic. Check if asp is a rule, and head is a single literal
        _, success = asp_parse_program([asp_dict])
        success = success[0]["code"] == 0
        if not success:
            error.append("Syntax error")
            continue
        parsed_asp = parse_line(asp)
        if parsed_asp.ast_type != ASTType.Rule:
            error.append("Syntax error: not rule")
            continue
        if parsed_asp.head.ast_type != ASTType.Literal:
            error.append("Syntax error: head should be a plain literal")
            continue

        # Heuristic. Goal should unify with the goal to prove.
        if find_bindings(goal, parsed_asp.unpool()[0].head) is None:
            error.append("Generated head does not unify to goal")
            continue

        const_list = asp_extract_const_list(asp, exclude_underscore=True)
        if polar_context.ontology_data is not None and polar_context.config.validate_ontology:
            missing_ontology = polar_context.find_missing_ontology(const_list)
            if len(missing_ontology) > 0: # missing ontology exists
                error.append(f"Missing ontology: {missing_ontology}")
                continue

        # If all satisfied, add to successful results.
        asp_dict["asp"] = asp
        result.append(asp_dict)
        error.append("Success")
    return result, error