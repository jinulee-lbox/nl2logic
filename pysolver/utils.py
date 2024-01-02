from copy import deepcopy
from clingo.ast import *
from clingo.symbol import *
import re
from enum import Enum

from .preprocess import preprocess

UNIT_FACTOR = {
    # Normal floats
    "": 1,
    # Numeric units
    "%" : 1,
    # Time units (second)
    "초": 1,
    "분": 60,
    "시간": 60*60,
    "일": 60*60*24,
    "주": 60*60*24*7,
    "주일": 60*60*24*7,
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
            return num * UNIT_FACTOR[unit]
        else:
            return input_string
    else:
        return input_string


def evaluate_num(ast: AST):
    result = _evaluate_num(ast)
    if result is not None:
        return SymbolicTerm(ast.location, String(str(result))) # simple numeric value to string.
    return ast

def _evaluate_num(ast: AST):
    # Evaluate ast into number (SymbolicTerm) if applicable.
    if ast.ast_type == ASTType.Variable:
        return None
    elif ast.ast_type == ASTType.SymbolicTerm:
        if ast.symbol.type == SymbolType.Number:
            return ast.symbol.number
        elif ast.symbol.type == SymbolType.String:
            string = convert_numeric_string_to_int(ast.symbol.string)
            if isinstance(string, int):
                return string
            else:
                return None
        else:
            return None
    elif ast.ast_type == ASTType.Function:
        # Predefined functions
        if ast.name == "round" and len(ast.arguments == 1):
            # round() function
            value = _evaluate_num(ast.arguments[0])
            if value is not None:
                return round(value)
            else:
                return None
    elif ast.ast_type == ASTType.UnaryOperation:
        if ast.operator_type == UnaryOperator.Minus:
            value = _evaluate_num(ast.arguments[0])
            if value is not None:
                return -value
            else:
                return None
    elif ast.ast_type == ASTType.BinaryOperation:
        value1 = _evaluate_num(ast.left)
        value2 = _evaluate_num(ast.right)
        if value1 is None or value2 is None:
            return None
        if ast.operator_type == BinaryOperator.Plus:
            return value1 + value2
        elif ast.operator_type == BinaryOperator.Minus:
            return value1 - value2
        elif ast.operator_type == BinaryOperator.Multiplication:
            return value1 * value2
        elif ast.operator_type == BinaryOperator.Division:
            return value1 - value2
        elif ast.operator_type == BinaryOperator.Power:
            return value1 ** value2
        elif ast.operator_type == BinaryOperator.Modulo:
            return value1 % value2
    return None

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

def extract_const_list(term: AST, exclude_underscore:bool = True):
    # Refer to official Potassco guide for details in Transformer.
    const_list = []
    class ConstantTracker(Transformer):
        def visit_SymbolicTerm(self, node):
            try:
                name = node.symbol.name
                arity = len(node.symbol.arguments)
                if not exclude_underscore or not name.startswith("_"):
                    const_list.append((name, arity))
                self.visit_children(node)
                return node # No change
            except Exception:
                # number, etc
                return node
        def visit_Function(self, node):
            name = node.name
            arity = len(node.arguments)
            if not exclude_underscore or not name.startswith("_"):
                const_list.append((name, arity))
            self.visit_children(node)
            return node # No change
    
    # parse_string converts string to AST.
    result = []
    try:
        if term.strip().endswith('.'):
            parse_string(term, result.append)
        # else, add a period and parse
        else:
            parse_string(term + ".", result.append)
        result = result[1]  # AST
        ConstantTracker()(result)
    except Exception as e:
        return []
    return const_list

def anonymize_vars(goal_str):
    return re.sub(r"([,( ])(_*[A-Z][A-Za-z_0-9]*)(?=[,)]| [+\-*/%><=!])", "\g<1>_", goal_str) # Remove variables

def parse_line(goal: str):
    # Convert all floating numbers (and integers) into string
    goal = re.sub(r"\b((-)?[0-9]+(\.[0-9]+)?)\b", r'"\g<1>"', goal)
    goal = goal.replace('""', '"')
    _temp = []
    parse_string(goal, callback=_temp.append)
    goal: AST = _temp[1]
    return goal

def parse_program(terms: list):
    success = []
    parsed_program = []
    for term in terms:
        # Parsing.
        try:
            parsed_program.extend(preprocess(parse_line(term['asp']))) # Unpack pooling and #count aggregates, negated heads to constraints, ...
        except Exception as e:
            success.append({
                'code': 10,
                'msg': "Syntax error " + str(e)
            })
            continue
        # Success code
        success.append({
            'code': 0,
            'msg': "Success"
        })
    assert len(terms) == len(success)
    return parsed_program, success

class RenameVariableState:
    def __init__(self):
        self._idx = 0
    
    def idx(self):
        temp = self._idx
        self._idx += 1
        return temp