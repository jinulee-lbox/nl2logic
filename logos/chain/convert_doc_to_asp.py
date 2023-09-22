import json
from typing import List, Dict, Any

from .components import *

# Top-down solver
from nl2logic.logic_utils.pysolver import *
from nl2logic.logic_utils.pysolver.preprocess import preprocess
from nl2logic.logic_utils.pysolver.run_proof import NOT_EXIST, USER_PROVED
from nl2logic.config import nl2logic_config as config

def convert_doc_to_asp(doc: Dict[str, Any]):
    """_summary_

    Args:
        doc (Dict[str, Any]): Dict with key `body_text` and `conclusion`. `conclusion` is a list of dict with keys `law_id` and `verdict`.
    """
    body_text = doc.pop("body_text")

    # Create initial program with related laws
    program = get_initial_program(doc)
    raw_program = [x["asp"] for x in program]
    preprocessed_program = "\n".join([preprocess(line) for line in raw_program]) + "\n"

    # Parse goals
    goals = get_goals(doc)

    # Retrieve information from config

    # Initialization
    for goal in goals:
        print("?-", goal)
        # Init current stack and visited goal marker
        stack = get_unproved_goals_from_preprocessed_program(preprocessed_program, goal, dict())
        visited = set(stack)

        while len(stack) > 0:
            curr_goal, unproved_reason = stack.pop()
            # if unproved_reason == USER_PROVED:
            #     continue
            print("Proving:", curr_goal)
            rule_examples = find_head_matching_examples(curr_goal, max_n=5) # TODO fix 5 -> config value
            rule_examples = find_random_examples(max_n=5-len(rule_examples)) + rule_examples
            print("Examples:")
            for ex in rule_examples: print(f"-    {ex['comment']}\n  -> {ex['asp']}")
            if len(rule_examples) > 0:
                new_asps = get_asp_and_rationale_with_examples(curr_goal, body_text, rule_examples)
            else:
                # Not reach here if find_random_examples() is called
                new_asps = get_asp_and_rationale_without_examples(curr_goal, body_text)
            # Check if valid
            # TODO
            valid_new_asps = validate_asp_list(new_asps, curr_goal)

            if len(valid_new_asps) > 0:
                for asp in valid_new_asps:
                    program.append(asp)
                    raw_program += asp["asp"] + "\n"
                    preprocessed_program += preprocess(asp["asp"])
                new_stack = [x for x in get_unproved_goals_from_preprocessed_program(preprocessed_program, goal, dict()) if x not in visited]
                visited.update(new_stack)
                stack += new_stack
        
        # Generate proof for goals
        proofs = get_proof_tree_from_preprocessed_program(preprocessed_program, goal, dict())
        if len(proofs) > 0:
            # Proof correctly generated
            print(proofs[0])
        else:
            pass
