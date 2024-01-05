import json
import logging
from typing import List, Dict, Any

from .components import *
from .utils.statement_to_text import statement_to_text

# Top-down solver
from pysolver import get_proof_tree
from pysolver.utils import unproved_goal_state_to_str, anonymize_vars, UnprovedGoalState
from pysolver.solve import solve, ProofContext
from pysolver.unify import equivalent
from .utils import config, PolarContext

retry_count = config.polar.retry_count

def abduction_factory(proof_context: ProofContext, body_text: str, polar_context: PolarContext):
    visited = []

    def abduction(state, unproved_reason: UnprovedGoalState):
        curr_goal = state.goal
        curr_goal_str = anonymize_vars(str(curr_goal)) # Remove variables

        # Check visited
        for visited_goal in visited:
            if equivalent(curr_goal, visited_goal):
                return False # do not proceed
        visited.append(curr_goal)

        logging.info("=======================")
        logging.info(f"Proving: {curr_goal_str}")
        
        # Retrieve examples from DB : TODO refactor this part
        rule_examples = find_examples(curr_goal, polar_context)

        # Generate ASP and rationale from the document.
        curr_retry_count=retry_count
        error_prompt = ""
        while curr_retry_count > 0:
            logging.info(f"Retry count: {curr_retry_count} left")
            curr_retry_count -= 1

            # Generate possible ASPs
            rationales = get_description_from_document(curr_goal_str, body_text, rule_examples, polar_context)
            if rationales is None:
                logging.info("LLM failed to generate valid JSON for rationales")
                continue
            result = []
            asp_dedup = set()
            for r in rationales:
                asps = get_statement_from_description(curr_goal_str, r, rule_examples, polar_context)
                for a in asps:
                    if a in asp_dedup:
                        continue
                    asp_dedup.add(a)
                    result.append({
                        "statement": a,
                        "comment": r
                    })

            # Check syntax & ontology
            valid_new_asps, error = validate_asp_list(result, curr_goal, polar_context)
            if len(valid_new_asps) == 0:
                error_prompt = ""
                for r, e in zip(result, error):
                    logging.info(f"LLM failed to generate valid ASP code: {str(r['asp'])} => {e}")
                    error_prompt += str(r['asp']) + "\n" + "Error: " + e
                continue
            logging.info(f"Hypo count {len(valid_new_asps)}")

            # Validate generated ASP
            proved = False
            error_prompt = "" # reset error prompt
            for asp in valid_new_asps:
                # Covnert ASP to string
                if config.polar.reformulate_description:
                    asp["comment_raw"] = asp["comment"]
                    asp["comment"] = get_description_from_statement(parse_line(asp["statement"]), polar_context)
                logging.info(json.dumps(asp, indent=4, ensure_ascii=False))
                # Perform self validation if mentioned in config
                do_self_validation = config.polar.self_validation
                if do_self_validation:
                    self_validation, self_val_fail_msg = validate_description_from_document(asp["comment"], body_text, polar_context)
                else:
                    self_validation = True
                # If self-validated by GPT,
                if self_validation:
                    # Validation complete
                    logging.info("=> Proved.")
                    # Update stack by adding new goals / remove unproved goals
                    proof_context.add_rule(asp)
                    
                    proved = True # end the loop
                else:
                    logging.info(f"=> Unproved. Reason: {self_val_fail_msg}")
                    error_prompt += str(asp["statement"]) + "\n" + "Error: Self-validation failed because: " + self_val_fail_msg
                    pass

            if proved:
                logging.info(f"Complete!")
                break
            else:
                logging.info("Generating valid ASP failed")
                logging.info("=======================")
                continue

        return True # call recursove_solve for current goal again

    return abduction

def generate_abductive_proof(doc: Dict[str, Any], polar_context: PolarContext):
    """_summary_

    Args:
        doc (Dict[str, Any]): Dict with key `body_text` and `conclusion`. `conclusion` is a list of dict with keys `law_id` and `verdict`.
    """

    body_text = doc.get("body_text")
    result_trees = []

    # Parse goal
    goal = parse_line(doc["goal"] + ".").head
    # Loop through goals to prove
    logging.info(f"?- {goal}.")

    # Create initial program with pre-defined rules
    program = doc['world_model']
    proof_context = ProofContext()
    for line in program:
        proof_context.add_rule(line)

    # Run solve with failure callback
    try:
        proofs = solve(
            goal,
            proof_context,
            unproved_callback=abduction_factory(proof_context, body_text, polar_context)
        )
    except RecursionError:
        logging.info("Proof cannot be completed due to infinite recursion, mainly due to the solver capacity.")
        return None, program

    # Analyze results
    logging.info(f"{len(proofs)} proofs found")
    # Generate proof tree
    proof = get_proof_tree(proof_context.program, goal)
    result_tree = proof
    program = proof_context.program
    # if proof is None:
    #     antiproof = get_proof_tree(proof_context.program, flip_sign(goal))
    #     result_tree = antiproof
    return result_tree, program
