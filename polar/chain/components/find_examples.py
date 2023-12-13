from random import shuffle

from clingo.ast import AST

from pysolver.unify import find_bindings
from pysolver.utils import get_hash_head, flip_sign, parse_line

from ..utils import PolarContext

def find_examples(curr_goal: AST, polar_context: PolarContext):
    if polar_context.example_data is None:
        return []

    few_shot_n = polar_context.config.few_shot_n
    few_shot_strategy = polar_context.config.few_shot_strategy

    if few_shot_strategy == "unify":
        rule_examples = find_head_matching_examples(curr_goal, polar_context)
        if polar_context.config.few_shot_randomfill and len(rule_examples) < few_shot_n:
            # Add random examples to match few_shot_n
            rule_examples = find_random_examples(few_shot_n-len(rule_examples), polar_context) + rule_examples
        # Truncate list
        rule_examples = rule_examples[-few_shot_n:]
    elif few_shot_strategy == "random":
        rule_examples = find_random_examples(few_shot_n, polar_context)
    else:
        raise ValueError(f"Undefined few_shot_strategy: {few_shot_strategy}")
    
    return rule_examples

def get_head_matching_terms(head: str, data):
    result = []
    for datum in data:
        if datum["statement"].startswith(head):
            result.append(datum)
    return result

def find_head_matching_examples(goal: AST, polar_context: PolarContext, max_n: int = None, more_related_goes_later=True):
    # Retrieve goals that share same prefix
    head = get_hash_head(goal)
    head_matching_terms = polar_context.get_head_matching_terms(head, polar_context.example_data)
    # Deduplicate terms to increase diversity
    dedup = set()
    head_matching_terms = [x for x in head_matching_terms if x["asp"] not in dedup and dedup.add(x["asp"]) is None]
    parsed_head_matching_terms = [parse_line(x["asp"]).head for x in head_matching_terms] # parse string to ASP
    pos_unifying_terms = [x for x, parsed in zip(head_matching_terms, parsed_head_matching_terms) if find_bindings(goal, parsed.unpool()[0]) is not None]
    pos_non_unifying_terms = [x for x in head_matching_terms if x not in pos_unifying_terms]
    shuffle(pos_unifying_terms)
    shuffle(pos_non_unifying_terms)

    # Retrieve goals that have negated prefix (a -> not a)
    head = get_hash_head(flip_sign(goal))
    head_matching_terms = polar_context.get_head_matching_terms(head)
    dedup = set()
    head_matching_terms = [x for x in head_matching_terms if x["asp"] not in dedup and dedup.add(x["asp"]) is None]
    parsed_head_matching_terms = [parse_line(x["asp"]).head for x in head_matching_terms] # parse string to ASP
    neg_unifying_terms = [x for x, parsed in zip(head_matching_terms, parsed_head_matching_terms) if find_bindings(goal, parsed.unpool()[0]) is not None]
    neg_non_unifying_terms = [x for x in head_matching_terms if x not in neg_unifying_terms]
    shuffle(neg_unifying_terms)
    shuffle(neg_non_unifying_terms)

    if more_related_goes_later:
        result = neg_non_unifying_terms + pos_non_unifying_terms + neg_unifying_terms + pos_unifying_terms
    else:
        result = pos_unifying_terms + neg_unifying_terms + pos_non_unifying_terms + neg_non_unifying_terms

    if max_n is not None:
        if len(result) <= max_n:
            return result
        else:
            if more_related_goes_later:
                return result[-max_n:]
            else:
                return result[:max_n]
    else:
        return result

def find_random_examples(max_n: int, polar_context: PolarContext):
    random_terms = polar_context.example_data[:]
    shuffle(random_terms)
    random_terms = random_terms[:min(max_n, len(random_terms))]
    return random_terms
