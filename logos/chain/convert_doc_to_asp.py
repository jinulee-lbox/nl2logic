import json
import logging
from typing import List, Dict, Any

from .components import *

# Top-down solver
from pysolver.utils import unproved_goal_state_to_str, anonymize_vars, UnprovedGoalState
from pysolver.solve import solve, ProofContext
from pysolver.unify import find_bindings
# from nl2logic.graphviz_utils import justification_tree_to_graphviz, graphviz_to_png
from nl2logic.config import nl2logic_config as config

get_key = lambda x: anonymize_vars(str(x[0])) if isinstance(x, tuple) else anonymize_vars(str(x))


def logos_add_new_rule_function_factory(context: ProofContext, body_text: str, few_shot_n: int=8, retry_count: int=3):
    visited = []

    def logos_add_new_rule(state, unproved_reason: UnprovedGoalState):
        curr_goal = state.goal

        # Check visited
        for visited_goal in visited:
            if find_bindings(curr_goal, visited_goal) is not None:
                return False # do not proceed
        visited.append(curr_goal)

        curr_goal_str = get_key(curr_goal) # Remove variables
        # curr_goal = parse_line(curr_goal_str + ".").head
        # if unproved_reason == USER_PROVED:
        #     continue
        logging.info("=======================")
        logging.info(f"Proving: {curr_goal_str}")
        
        # Retrieve examples from DB : TODO refactor this part
        rule_examples = []
        rule_examples.extend(find_head_matching_examples(curr_goal))
        if len(rule_examples) < few_shot_n:
            # Add random examples to match few_shot_n
            # rule_examples = find_random_examples(max_n=few_shot_n-len(rule_examples)) + rule_examples
            pass
        else:
            # Select valid examples (at the back of the list, by find_head_matching_example param `more_related_goes_later`)
            rule_examples = rule_examples[-few_shot_n:]
        logging.info("---------------------")
        logging.info("Examples:")
        for ex in rule_examples: logging.info(f"-    {ex['comment']}\n  -> {ex['asp']}")
        logging.info("---------------------")

        # Core step! generate ASP and rationale from the document.
        proved = False; curr_retry_count=retry_count
        error_prompt = None
        while not proved and curr_retry_count > 0:
            logging.info(f"Retry count: {curr_retry_count} left")
            curr_retry_count -= 1

            # Generate possible ASPs
            result = get_asp_and_rationale_from_doc(curr_goal, curr_goal_str, body_text, rule_examples, error_prompt)
            if result is None:
                logging.info("LLM failed to generate valid JSON")
                continue

            # Syntax / Ontology checking
            valid_new_asps, error = validate_asp_list(result, curr_goal)
            if len(valid_new_asps) == 0:
                error_prompt = ""
                for r, e in zip(result, error):
                    logging.info(f"LLM failed to generate valid ASP code: {str(r['asp'])} => {e}")
                    error_prompt += str(r['asp']) + "\n" + "Error: " + e
                continue

            # Generate
            logging.info(f"Hypo count {len(valid_new_asps)}")
            if len(valid_new_asps) > 0:
                for asp in valid_new_asps:
                    # Covnert ASP to string
                    asp["comment_raw"] = asp["comment"]
                    asp["comment"] = get_rationale_from_asp(parse_line(asp["asp"]))
                    logging.info(json.dumps(asp, indent=4, ensure_ascii=False))
                    if asp["source"] in ["commonsense"] or validate_rationale_from_doc(asp["comment"], body_text):
                        # Validation complete
                        logging.info("=> Proved.")
                        # Update stack by adding new goals / remove unproved goals
                        context.add_rule(asp)
                        
                        proved = True # end the loop
                    else:
                        logging.info("=> Unproved.")
                        pass
            else:
                logging.info("- No proofs to be analyzed")
                pass

            if proved:
                logging.info(f"Complete!")
            else:
                logging.info("Generating valid ASP failed")
            logging.info("=======================")
        
            # if graph_output_path is not None:
            #     # Generate proof for goals
            #     proof = get_proof_tree(preprocessed_program, goal, dict())
            #     if proof:
            #         viz_tree = justification_tree_to_graphviz(proof)
            #     else:
            #         antiproof = get_proof_tree(preprocessed_program, 'not ' + goal, dict())
            #         viz_tree = justification_tree_to_graphviz(antiproof)
            #     graphviz_to_png(viz_tree, graph_output_path + "/" + str(iter_count) + ".svg")
        return True # call recursove_solve for current goal again

    return logos_add_new_rule

def convert_doc_to_asp(doc: Dict[str, Any], few_shot_n=5, retry_count=3, graph_output_path=None):
    """_summary_

    Args:
        doc (Dict[str, Any]): Dict with key `body_text` and `conclusion`. `conclusion` is a list of dict with keys `law_id` and `verdict`.
    """

    body_text = doc.get("body_text")

    # Create initial program with related laws
    program = get_initial_program(doc)
    raw_program = [x["asp"] for x in program]
    print("\n".join(raw_program))
    # Parse goals
    goals = get_goals(doc)
    # Loop through goals to prove
    for goal in goals:
        logging.info(f"?- {goal}.")
        # print(preprocessed_program)

        context = ProofContext()
        for line in program:
            context.add_rule(line)

        proofs = solve(
            goal,
            context,
            unproved_callback=logos_add_new_rule_function_factory(context, body_text)
        )
        logging.info(len(proofs), "proofs found")
        if len(proofs) > 0:
            logging.info(proofs[0])
                
        # Generate proof for goals
        # proof, proved = get_proof_tree(preprocessed_program, goal, dict())
        # if proved:
        #     result_trees.append(proof)
        # else:
        #     antiproof = get_proof_tree(preprocessed_program, 'not ' + goal, dict())
        #     result_trees.append(antiproof)
    # return result_trees, program
    return None, program
