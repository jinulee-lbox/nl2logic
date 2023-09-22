from typing import List
import re

from clingo.ast import *
from clingo.symbol import *
from .utils import get_hash_head

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
    for rule_idx, rule_str in enumerate(program):
        if len(rule_str.strip()) == 0:
            continue
        elif rule_str.strip().startswith("% "):
            label = rule_str.replace("% ", "")
            continue

        rule_str = re.sub(r"([,( ])(_*[A-Z][A-Za-z_0-9]*)(?=[,)]| [+\-*/%><=!])", f"\g<1>\g<2>_{rule_idx}", rule_str) # attatch rule_idx to ordinary(non-anonymous) variables
        anonym_idx = 0
        while True:
            rule_str, replaced = re.subn(r"([,( ])_(?=[,)]| [+\-*/%><=!])", f"\g<1>_Anon_{rule_idx}_{anonym_idx}", rule_str, count=1)
            if replaced == 0:
                break
            anonym_idx += 1

        rule = parse_line(rule_str)

        # Remove location inforamtion for efficiency
        # remove_location(rule)

        parsed_rules.append(rule)
        is_dual = r"% dual" in rule_str
        
        hash_head = get_hash_head(rule)
        if hash_head not in parsed_rule_dict:
            parsed_rule_dict[hash_head] = []
        parsed_rule_dict[hash_head].append((rule, is_dual))
        label_rule_dict[label] = rule
    return parsed_rule_dict, label_rule_dict

def parse_line(goal: str):
    _temp = []
    parse_string(goal, callback=_temp.append)
    goal: AST = _temp[1]
    return goal