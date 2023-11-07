from typing import List
from copy import deepcopy
import itertools

from clingo.ast import SymbolicAtom
from clingo.ast import *
from clingo.control import *
from clingo.symbol import *

from .utils import convert_numeric_string_to_int

def powerset(iterable):
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))

def unpack_count_aggregates(term: AST) -> List[AST]:
    # {a; b; c} -> a or b or c
    assert term.ast_type == ASTType.Rule
    body = term.body

    new_body = []
    new_rules = []

    for body_lit in body:
        if body_lit.ast_type == ASTType.Literal:
            body_atom = body_lit.atom
            if body_atom.ast_type in [ASTType.Aggregate, ASTType.BodyAggregate]:
                # Found aggregate
                if body_atom.ast_type == ASTType.BodyAggregate and body_atom.function != AggregateFunction.Count:
                    raise ValueError(f"Do not support Aggregate function {body_atom.function}")

                new_body.append(
                    [[(deepcopy(lit).literal)]
                        for lit in body_atom.elements]
                )
            else:
                # Non-aggregate
                new_body.append([[body_lit]])

    # Create all possible rules
    for unpacked_body in itertools.product(*new_body):
        # Flatten list
        unpacked_body = [item for sublist in unpacked_body for item in sublist]
        # Add new rules
        new_rule = Rule(
            term.location,
            term.head,
            unpacked_body
        )
        new_rules.append(new_rule)

    return new_rules

def get_dual(rule: AST) -> List[AST]:
    assert rule.ast_type == ASTType.Rule
    rule = deepcopy(rule)

    head = rule.head
    if not (head.ast_type == ASTType.Literal and head.atom.ast_type == ASTType.SymbolicAtom):
        if 'atom' not in head.child_keys:
            return [] # Do nothing
        elif head.atom.ast_type == ASTType.BooleanConstant:
            return [] # Do nothing
        raise ValueError("All rule heads must be non-conditional simple literals")
    if head.sign == Sign.Negation:
        return [] # If rule is `not a :- ...` -> do not create duals
    # head.sign = Sign.NoSign if head.sign == Sign.Negation else Sign.Negation
    head.sign = Sign.Negation

    # Flip body literal one by one as in s(CASP).
    body_cnt = len(rule.body)
    dual_rules = []
    for i in range(body_cnt):
        body_lits = []
        # append body literals
        for j in range(i):
            body_lits.append(rule.body[j])
        # flip i-th body literal
        dual_body_lit = deepcopy(rule.body[i])
        dual_body_lit.sign = Sign.NoSign if dual_body_lit.sign == Sign.Negation else Sign.Negation
        body_lits.append(dual_body_lit)
        # create new rules
        dual_rules.append(Rule(
            rule.location,
            head,
            body_lits
        ))
    return dual_rules
    
def get_explicit_dual(rule:AST) -> List[AST] :
    assert rule.ast_type == ASTType.Rule
    rule = deepcopy(rule)

    head = rule.head
    if not (head.ast_type == ASTType.Literal and head.atom.ast_type == ASTType.SymbolicAtom):
        if 'atom' not in head.child_keys:
            return [] # Do nothing
        elif head.atom.ast_type == ASTType.BooleanConstant:
            return [] # Do nothing
        raise ValueError("All rule heads must be non-conditional simple literals")
    
    if head.sign == Sign.NoSign:
        original_head = deepcopy(head)
        # Flip to body as integrity constriant
        if head.atom.symbol.ast_type in [ASTType.Function, ASTType.SymbolicTerm]:
            # not a() :-
            head.atom.symbol = UnaryOperation(
                head.location,
                UnaryOperator.Minus,
                deepcopy(head)
            )
            head.sign = Sign.Negation
            return [Rule(
                rule.location,
                head,
                [original_head]
            )]
        elif head.atom.symbol.ast_type == ASTType.UnaryOperation and head.atom.symbol.operator_type == UnaryOperator.Minus:
            # not -a() :-
            # Get the (classically) negated term,
            head.atom.symbol = head.atom.symbol.argument
            if head.atom.symbol.ast_type == ASTType.Function:
                # not -a() :-
                head.sign = Sign.Negation
                return [Rule(
                    rule.location,
                    head,
                    [original_head]
                )]
            elif head.atom.symbol.ast_type == ASTType.SymbolicTerm:
                # not -a :-
                head.sign = Sign.Negation
                return [Rule(
                    rule.location,
                    head,
                    [original_head]
                )]
    return []

def get_constraints(rule:AST) -> [AST] :
    assert rule.ast_type == ASTType.Rule
    rule = deepcopy(rule)
    constraints = []

    head = rule.head
    if not (head.ast_type == ASTType.Literal and head.atom.ast_type == ASTType.SymbolicAtom):
        if 'atom' not in head.child_keys:
            return [] # Do nothing
        elif head.atom.ast_type == ASTType.BooleanConstant:
            return [] # Do nothing
        raise ValueError("All rule heads must be non-conditional simple literals")
    
    if head.sign == Sign.Negation:
        # Flip to body as integrity constriant
        head.sign = Sign.NoSign
        rule.body.append(deepcopy(head))
        rule.head = BooleanConstant(0)
        constraints.append(rule)
    elif head.sign == Sign.NoSign and head.atom.symbol.ast_type == ASTType.UnaryOperation and head.atom.symbol.operator_type == UnaryOperator.Minus:
        # -a(X) -> new constraints!!!
        constraints.append(Rule(
            location=rule.location,
            head = BooleanConstant(0),
            body = [
                deepcopy(head.atom.symbol),
                deepcopy(head.atom.symbol.argument)
            ] # -a and a cannot hold together!!
        ))
    return constraints

def translate_numeric_string(rule:AST) -> AST:
    # Recursive search, and apply `utils.convert_numeric_string_to_int` for all str
    def convert_num_str(term: AST) -> AST:
        new_term = deepcopy(term) # value to return
        if term.ast_type == ASTType.UnaryOperation:
            new_argument = convert_num_str(term.argument)
            new_term.argument = new_argument
        elif term.ast_type == ASTType.BinaryOperation:
            new_left = convert_num_str(term.left)
            new_right = convert_num_str(term.right)
            new_term.left = new_left
            new_term.right = new_right
        elif term.ast_type == ASTType.Function:
            new_arguments = []
            for argument in term.arguments:
                new_arguments.append(convert_num_str(argument))
            new_term.arguments = new_arguments
        elif term.ast_type == ASTType.SymbolicTerm:
            if term.symbol.type == SymbolType.String:
                new_str = convert_numeric_string_to_int(term.symbol.string)
                if isinstance(new_str, int):
                    new_term = SymbolicTerm(
                        location=term.location,
                        symbol=Number(new_str)
                    )
        elif term.ast_type == ASTType.Variable:
            pass
        else:
            raise ValueError(f"Unsupported type {term.ast_type}")
        return new_term

    if rule.head.ast_type == ASTType.Literal:
        if 'atom' not in rule.head.child_keys:
            pass
        elif rule.head.atom.ast_type == ASTType.BooleanConstant:
            pass # Do nothing
        else:
            rule.head.atom.symbol = convert_num_str(rule.head.atom.symbol)
    elif rule.head.ast_type == ASTType.BooleanConstant:
        pass # do nothing

    for body_lit in rule.body:
        if body_lit.atom.ast_type == ASTType.SymbolicAtom:
            body_lit.atom.symbol = convert_num_str(body_lit.atom.symbol)
        elif body_lit.atom.ast_type == ASTType.Comparison:
            body_lit.atom.term = convert_num_str(body_lit.atom.term)
            for guard in body_lit.atom.guards:
                guard.term = convert_num_str(guard.term)
    return rule

def preprocess(term_str):
    """Translate s(CASP) format with...
    - Unpack OR statement aggregates
    - Unpack pooling

    Args:
        term_str (str): String to parse. Might raise syntax error if parsing is failed

    Raises:
        ValueError: _description_
        ValueError: _description_

    Returns:
        str: String file including expanded ruleset.
    """
    term_temp = []
    parse_string(term_str, term_temp.append)
    term = term_temp[1]

    new_rules = ""

    if term.ast_type == ASTType.Rule:
        unpacked_count_terms = unpack_count_aggregates(term)
        
        unpooled_terms = []
        for term in unpacked_count_terms:
            unpooled_terms.extend(term.unpool())

        for t3 in unpooled_terms:
            t3 = translate_numeric_string(t3)
            new_rules += str(t3) + "\n"

            # Dual statements
            for dual in get_dual(t3):
                new_rules += str(dual) + r" % dual" + "\n"
            # not pred :- -pred DISABLED TO PREVENT INFINITE LOOPS
            for explicit_dual in get_explicit_dual(t3):
                new_rules += str(explicit_dual) + r" % dual" + "\n"
            # :- a, -a
            for constraint in get_constraints(t3):
                new_rules += str(constraint) + "\n"

    return "% " + str(term) + "\n" + new_rules