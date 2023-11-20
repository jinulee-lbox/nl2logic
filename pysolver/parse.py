from typing import List
import re

from clingo.ast import *
from clingo.symbol import *
from .utils import get_hash_head, parse_line

def parse_program(program: str):
    program = program.split("\n")
    # Remove duplicate lines
    seen = set()
    seen_add = seen.add
    program = [x for x in program if not (x in seen or seen_add(x))]
    
    parsed_rules = []
    parsed_rule_dict = {}
    label_rule_dict = {}
    label = None
    for rule_str in program:
        if len(rule_str.strip()) == 0:
            continue
        elif rule_str.strip().startswith("% "):
            label = rule_str.replace("% ", "")
            continue

        rule = parse_line(rule_str)

        # Remove location inforamtion for efficiency
        # remove_location(rule)

        parsed_rules.append(rule)
        
        hash_head = get_hash_head(rule)
        if hash_head not in parsed_rule_dict:
            parsed_rule_dict[hash_head] = []
        parsed_rule_dict[hash_head].append(rule)
        label_rule_dict[label] = rule
    return parsed_rule_dict, label_rule_dict