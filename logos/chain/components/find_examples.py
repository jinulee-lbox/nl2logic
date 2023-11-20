from random import shuffle

from clingo.ast import AST

from nl2logic.logic_utils.pysolver.parse import parse_line
from nl2logic.logic_utils.pysolver.unify import find_bindings
from nl2logic.logic_utils.pysolver.utils import get_hash_head, flip_sign

from nl2logic.database_utils.queries import db_get_head_matching_terms, db_get_random_terms

def find_head_matching_examples(goal: AST, max_n: int = None, more_related_goes_later=True):
    # Retrieve goals that share same prefix
    head = get_hash_head(goal)
    head_matching_terms = db_get_head_matching_terms(head)
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
    head_matching_terms = db_get_head_matching_terms(head)
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

def find_random_examples(max_n: int):
    random_terms = db_get_random_terms(max_n)
    return random_terms
