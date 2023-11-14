from copy import deepcopy
from clingo.ast import *
from clingo.symbol import *
import re
from enum import Enum

UNIT_FACTOR = {
    # Numeric units
    "%" : 1000,
    # Time units (second)
    "초": 1,
    "분": 60,
    "시간": 60*60,
    "일": 60*60*24,
    "주": 60*60*24*7,
    "개월": 60*60*24*30,
    "년": 60*60*24*365,
    # Distance units (mm)
    "m": 1000,
    "km": 1000000,
    # Weight units (g)
    "g": 1,
    "kg": 1000,
    # etc.
    "차로": 1,
    "차선": 1,
    "원": 1,
    "도": 1000,
}
# Markers for unproved goals
class UnprovedGoalState(Enum):
    NOT_EXIST = 0
    UNPROVED_YET = 1
    BACKTRACK = 2

def unproved_goal_state_to_str(failure):
    if failure == UnprovedGoalState.NOT_EXIST:
        return "NOT_EXIST"
    if failure == UnprovedGoalState.UNPROVED_YET:
        return "UNPROVED_YET"
    if failure == UnprovedGoalState.BACKTRACK:
        return "BACKTRACK"
    else:
        raise ValueError("Wrong failed-goal-marker")

def convert_numeric_string_to_int(input_string):
    pattern = r'^([-+]?\d{1,3}(?:,\d{3})*(\.\d+)?)|^([-+]?\d+(\.\d*)?)'
    match = re.match(pattern, input_string)
    
    if match:
        if input_string.isnumeric():
            return int(input_string)
        num_str = match.group()
        unit = input_string.replace(num_str, "")
        num = float(num_str.replace(",",""))
        if unit in UNIT_FACTOR:
            # print(num, unit)
            return int(num * UNIT_FACTOR[unit])
        else:
            return input_string
    else:
        return input_string

def get_hash_head(ast:AST):
    rule_str = str(ast)
    # Hash by head symbol (rule base..^^)
    # not a(..) :-   =>    `not a`
    # if rule_str.startswith("")
    index1 = rule_str.index(":-") if ":-" in rule_str else 1000000
    index2 = rule_str.index("(") if "(" in rule_str else 1000000
    index3 = rule_str.index(".") if "." in rule_str else 1000000
    index = min(index1, index2, index3)
    if index == 1000000:
        return rule_str
    hash_head = rule_str[:index].strip()
    return hash_head

def is_negated(ast: AST) -> bool:
    if ast.ast_type != ASTType.Literal:
        raise ValueError(f"AST {str(ast)} is not Literal; thus cannot be negated")
    return ast.sign == Sign.Negation

def is_ground(ast: AST) -> bool:
    # Only true if no variables are inside this ast.
    if ast.ast_type == ASTType.Variable:
        return False
    
    # Literals
    if "atom" in ast.child_keys:
        return is_ground(ast.atom)
    # Terms
    grounded = True
    if "arguments" in ast.child_keys:
        for arg in ast.arguments:
            grounded &= is_ground(arg)
            if not grounded: # Early termination (time cutting)
                return False
    if "left" in ast.child_keys:
        grounded &= is_ground(ast.left)
    if "right" in ast.child_keys:
        grounded &= is_ground(ast.right)
    if "argument" in ast.child_keys:
        grounded &= is_ground(ast.argument)
    if "symbol" in ast.child_keys:
        grounded &= is_ground(ast.symbol)
    if "term" in ast.child_keys:
        grounded &= is_ground(ast.term)
    if "guards" in ast.child_keys:
        for arg in ast.guards:
            grounded &= is_ground(arg.term)
    return grounded

def flip_sign(ast):
    new_ast = deepcopy(ast)
    if ast.sign == Sign.Negation:
        new_ast.sign = Sign.NoSign
    elif ast.sign == Sign.NoSign:
        new_ast.sign = Sign.Negation
    else:
        raise ValueError("Does not support DoubleNegation")
    return new_ast

def anonymize_vars(goal_str):
    return re.sub(r"([,( ])(_*[A-Z][A-Za-z_0-9]*)(?=[,)]| [+\-*/%><=!])", "\g<1>_", goal_str) # Remove variables

def parse_line(goal: str):
    _temp = []
    parse_string(goal, callback=_temp.append)
    goal: AST = _temp[1]
    return goal

class RenameVariableState:
    def __init__(self):
        self._idx = 0
    
    def idx(self):
        temp = self._idx
        self._idx += 1
        return temp

def rename_variables(rule: AST, rename_var_state: RenameVariableState) -> AST:
    rule_str = str(rule)
    rule_str = re.sub(r"([,( ])(_*[A-Z][A-Za-z_0-9]*)(?=[,)]| [+\-*/%><=!])", f"\g<1>\g<2>_{rename_var_state.idx()}", rule_str) # attatch rule_idx to ordinary(non-anonymous) variables
    anonym_idx = 0
    while True:
        rule_str, replaced = re.subn(r"([,( ])_(?=[,)]| [+\-*/%><=!])", f"\g<1>_Anon_{rename_var_state.idx()}_{anonym_idx}", rule_str, count=1)
        if replaced == 0:
            break
        anonym_idx += 1
    return parse_line(rule_str)