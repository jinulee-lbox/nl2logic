import json
import logging
from typing import List, Dict, Any

from .components import *

# Top-down solver
from nl2logic.logic_utils.pysolver import *
from nl2logic.logic_utils.pysolver.preprocess import preprocess
from nl2logic.logic_utils.pysolver.utils import failure_code_to_str, anonymize_vars
from nl2logic.logic_utils.api import asp_extract_const_list
from nl2logic.graphviz_utils import justification_tree_to_graphviz, graphviz_to_png
from nl2logic.config import nl2logic_config as config

get_key = lambda x: anonymize_vars(str(x[0])) if isinstance(x, tuple) else anonymize_vars(str(x))

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
    # END DEBUG
    preprocessed_program = "\n".join([preprocess(line) for line in raw_program]) + "\n"

    # Parse goals
    goals = get_goals(doc)

    # Retrieve information from config

    # Named entity recognition
    # frame = get_frame_instance("operateVehicle", body_text)
    # exit()
    # entities = get_named_entity_recognition(body_text)
    # print(entities)

    # Initialization
    result_trees = []
    for goal in goals:
        logging.info(f"?- {goal}")
        # Init current stack and visited goal marker
        stack = get_unproved_goals_from_preprocessed_program(preprocessed_program, goal, dict())
        # Deduplicate initial stack
        dedup = set()
        stack = [x for x in stack if get_key(x) not in dedup and dedup.add(get_key(x)) is None] # deduplicate within stack
        visited = set()

        if graph_output_path is not None:
            # Generate proof for goals
            proof, proved = get_proof_tree_from_preprocessed_program(preprocessed_program, goal, dict())
            if proved:
                viz_tree = justification_tree_to_graphviz(proof)
            else:
                antiproof, _ = get_proof_tree_from_preprocessed_program(preprocessed_program, 'not ' + goal, dict())
                viz_tree = justification_tree_to_graphviz(antiproof)
            graphviz_to_png(viz_tree, graph_output_path + "/0.svg")

        iter_count = 0
        while len(stack) > 0:
            iter_count += 1
            logging.info("STACK:")
            logging.info([str(x[0]) + " / " + failure_code_to_str(x[1]) for x in stack])
            curr_goal, unproved_reason = stack.pop()
            curr_goal_str = get_key(curr_goal) # Remove variables
            visited.add(curr_goal_str) # Memoization
            # if unproved_reason == USER_PROVED:
            #     continue
            logging.info("=======================")
            logging.info(f"Proving: {curr_goal}")

            # Retrieve examples from DB
            rule_examples = []
            raw_rule_examples = find_head_matching_examples(curr_goal)
            for rule_example in raw_rule_examples:
                # if rule_example["source"] in ["commonsense"] and rule_example["asp"] not in commonsense_check:
                #     # Commonsesne statements can apply to all documents
                #     commonsense_asps.append(rule_example)
                #     commonsense_check.add(rule_example["asp"])
                # else:
                    rule_examples.append(rule_example)
            if len(rule_examples) < few_shot_n:
                # Add random examples to match few_shot_n
                rule_examples = find_random_examples(max_n=few_shot_n-len(rule_examples)) + rule_examples
            else:
                # Select valid examples (at the back of the list, by find_head_matching_example param `more_related_goes_later`)
                rule_examples = rule_examples[-few_shot_n:]
            # logging.info("---------------------")
            # logging.info("Examples:")
            # for ex in rule_examples: logging.info(f"-    {ex['comment']}\n  -> {ex['asp']}")
            # logging.info("---------------------")

            # Core step! generate ASP and rationale from the document.
            proved = False; curr_retry_count=retry_count
            while not proved and curr_retry_count > 0:
                logging.info(f"Retry count: {curr_retry_count} left")
                curr_retry_count -= 1

                # Generate possible ASPs
                result = get_asp_and_rationale_from_doc(curr_goal_str, body_text, rule_examples)
                if result is None:
                    logging.info("LLM failed to generate valid JSON")
                    continue

                # Syntax / Ontology checking
                valid_new_asps = validate_asp_list(result, curr_goal)
                if len(valid_new_asps) == 0:
                    logging.info("LLM failed to generate valid ASP code(syntax error, ontology, ...)")
                    continue

                # Generate
                logging.info(f"Hypo count {len(valid_new_asps)}")
                if len(valid_new_asps) > 0:
                    for asp in valid_new_asps:
                        # Covnert ASP to string
                        asp["comment_raw"] = asp["comment"]
                        asp["comment"] = get_rationale_from_asp(parse_line(asp["asp"]), asp["comment"], rule_examples)
                        logging.info(json.dumps(asp, indent=4, ensure_ascii=False))
                        if asp["source"] in ["commonsense"] or validate_rationale_from_doc(asp["comment"], body_text):
                            logging.info("=> Proved.")
                            # Validation complete
                            program.append(asp)
                            raw_program.append(asp["asp"])
                            preprocessed_program += preprocess(asp["asp"])
                            # Update stack by adding new goals / remove unproved goals
                            new_stack = get_unproved_goals_from_preprocessed_program(preprocessed_program, goal, dict())
                            new_stack = [x for x in new_stack if get_key(x) not in visited] # deduplicate within already checked goals
                            dedup = set()
                            new_stack = [x for x in new_stack if get_key(x) not in dedup and dedup.add(get_key(x)) is None] # deduplicate within stack
                            stack = new_stack
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
        
            if graph_output_path is not None:
                # Generate proof for goals
                proof, proved = get_proof_tree_from_preprocessed_program(preprocessed_program, goal, dict())
                if proved:
                    viz_tree = justification_tree_to_graphviz(proof)
                else:
                    antiproof, _ = get_proof_tree_from_preprocessed_program(preprocessed_program, 'not ' + goal, dict())
                    viz_tree = justification_tree_to_graphviz(antiproof)
                graphviz_to_png(viz_tree, graph_output_path + "/" + str(iter_count) + ".svg")
                
        # Generate proof for goals
        proof, proved = get_proof_tree_from_preprocessed_program(preprocessed_program, goal, dict())
        if proved:
            result_trees.append(proof)
        else:
            antiproof, _ = get_proof_tree_from_preprocessed_program(preprocessed_program, 'not ' + goal, dict())
            result_trees.append(antiproof)
    return result_trees, program
