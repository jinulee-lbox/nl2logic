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
                flip_inequal = { # Flip inequlality direction for left_guard
                    ComparisonOperator.GreaterEqual : ComparisonOperator.LessEqual,
                    ComparisonOperator.GreaterThan : ComparisonOperator.LessThan,
                    ComparisonOperator.LessEqual : ComparisonOperator.GreaterEqual,
                    ComparisonOperator.LessThan : ComparisonOperator.GreaterThan,
                }

                # Generate length constraint
                comparison = []; bound = []
                try:
                    if body_atom.left_guard is not None:
                        comparison.append(flip_inequal[body_atom.left_guard.comparison])
                        bound.append(body_atom.left_guard.term.symbol.number)
                    if body_atom.right_guard is not None:
                        comparison.append(body_atom.right_guard.comparison)
                        bound.append(body_atom.right_guard.term.symbol.number)
                except:
                    # Non-const boundaries
                    raise ValueError("Do not support variable boundaries for Aggregates")
                # FIXME: Expanding count aggregates do not work properly when dual-ed.
                # For now, only accept lower bounds
                assert len(comparison) == 1
                assert comparison[0] in [ComparisonOperator.GreaterThan, ComparisonOperator.GreaterEqual]

                powerset_of_aggregates = []
                # FIXME: only accept lower bounds for now (dual causes some problem for count)
                # Change this to global constraints
                # (i.e. a :- {b;c;d}<3 => :- a;b;c;d.)
                for accept_set in powerset(list(range(len(body_atom.elements)))):
                    # Check length constraints
                    flag = True
                    for comp, bnd in zip(comparison, bound):
                        if comp == ComparisonOperator.GreaterEqual:
                            flag = flag and len(accept_set) == bnd
                        elif comp == ComparisonOperator.GreaterThan:
                            flag = flag and len(accept_set) == bnd+1
                    if not flag:
                        continue
                    powerset_of_aggregates.append(
                        [(deepcopy(lit).literal)
                         for i, lit in enumerate(body_atom.elements) if i in accept_set]
                    )
                # for accept_set in powerset(list(range(len(body_atom.elements)))):
                #     # Check length constraints
                #     flag = True
                #     for comp, bnd in zip(comparison, bound):
                #         if comp == ComparisonOperator.GreaterEqual:
                #             flag = flag and len(accept_set) >= bnd
                #         elif comp == ComparisonOperator.GreaterThan:
                #             flag = flag and len(accept_set) > bnd
                #         elif comp == ComparisonOperator.LessEqual:
                #             flag = flag and len(accept_set) <= bnd
                #         else: # comp == ComparisonOperator.LessThan:
                #             flag = flag and len(accept_set) < bnd
                #     if not flag:
                #         continue
                #     def negate(lit: AST):
                #         if lit.sign == Sign.Negation:
                #             lit.sign = Sign.NoSign
                #         if lit.sign == Sign.NoSign:
                #             lit.sign = Sign.Negation
                #         return lit
                #     # Collect subsets
                #     powerset_of_aggregates.append(
                #         [(deepcopy(lit).literal if i in accept_set else negate(deepcopy(lit).literal))
                #          for i, lit in enumerate(body_atom.elements)]
                #     )
                new_body.append(powerset_of_aggregates)
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

def unpack_pool(term):
    # assert term.ast_type in [ASTType.UnaryOperation, ASTType.BinaryOperation, ASTType.Function, ASTType.Pool, ASTType.SymbolicTerm]
    terms = []

    if term.ast_type == ASTType.UnaryOperation:
        new_arguments = unpack_pool(term.argument)
        for new_argument in new_arguments:
            new_term = deepcopy(term)
            new_term.argument = new_argument
            terms.append(new_term)
    elif term.ast_type == ASTType.BinaryOperation:
        new_lefts = unpack_pool(term.left)
        new_rights = unpack_pool(term.right)
        for new_left in new_lefts:
            for new_right in new_rights:
                new_term = deepcopy(term)
                new_term.left = new_left
                new_term.right = new_right
                terms.append(new_term)
    elif term.ast_type == ASTType.Function:
        new_arguments_pow = []
        for argument in term.arguments:
            new_arguments_pow.append(unpack_pool(argument))
        for new_arguments in itertools.product(*new_arguments_pow):
            assert len(new_arguments) == len(term.arguments)
            new_term = deepcopy(term)
            new_term.arguments = new_arguments
            terms.append(new_term)
    elif term.ast_type == ASTType.Pool:
        new_arguments_pow = []
        for argument in term.arguments:
            new_arguments_pow.append(unpack_pool(argument))
        for new_arguments in itertools.product(*new_arguments_pow):
            assert len(new_arguments) == len(term.arguments)
            terms.extend(new_arguments)
            # terms = new_arguments + terms # To obtain proper tree, move pool infront of other predicates.
    elif term.ast_type == ASTType.SymbolicTerm or term.ast_type == ASTType.Variable:
        terms = [term]
    else:
        raise ValueError(f"Unsupported type {term.ast_type}")

    assert len(terms) >= 1


    return terms

def unpack_head_pool(rule: AST) -> List[AST] :
    assert rule.ast_type == ASTType.Rule

    head = rule.head
    if not (head.ast_type == ASTType.Literal and head.atom.ast_type == ASTType.SymbolicAtom):
        if head.atom.ast_type == ASTType.BooleanConstant:
            return [rule] # Do nothing
        raise ValueError(f"All rule heads must be non-conditional simple literals.")

    heads = unpack_pool(head.atom.symbol) # recursively find pools

    new_rules = [
        Rule(
            location=rule.location,
            head=Literal(
                location=head.location,
                sign=head.sign,
                atom=SymbolicAtom(
                    symbol=new_head
                )
            ),
            body=rule.body
        ) for new_head in heads
    ]

    return new_rules

def unpack_body_pool(rule:AST) -> str :
    assert rule.ast_type == ASTType.Rule
    body = rule.body

    new_body = []
    new_rules = []

    for body_lit in body:
        if body_lit.ast_type == ASTType.Literal:
            if body_lit.atom.ast_type == ASTType.SymbolicAtom:
                new_body.append(
                    [Literal(
                        location=body_lit.location,
                        sign=body_lit.sign,
                        atom=SymbolicAtom(
                            symbol=symbol
                        )
                    ) for symbol in unpack_pool(body_lit.atom.symbol)]
                )
            else:
                # Comparison or boolean constant
                new_body.append([body_lit])
        else:
            raise ValueError(f"Body contains {body_lit.ast_type}, which is unsupported")

    # Create all possible rules
    for unpacked_body in itertools.product(*new_body):
        # Add new rules
        new_rule = Rule(
            rule.location,
            rule.head,
            unpacked_body
        )
        new_rules.append(new_rule)

    return new_rules

def get_dual(rule: AST) -> List[AST]:
    assert rule.ast_type == ASTType.Rule
    rule = deepcopy(rule)

    head = rule.head
    if not (head.ast_type == ASTType.Literal and head.atom.ast_type == ASTType.SymbolicAtom):
        if head.atom.ast_type == ASTType.BooleanConstant:
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
        if head.atom.ast_type == ASTType.BooleanConstant:
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

def get_constraints(rule:AST) -> [AST] :
    assert rule.ast_type == ASTType.Rule
    rule = deepcopy(rule)
    constraints = []

    head = rule.head
    if not (head.ast_type == ASTType.Literal and head.atom.ast_type == ASTType.SymbolicAtom):
        if head.atom.ast_type == ASTType.BooleanConstant:
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
        if rule.head.atom.ast_type == ASTType.BooleanConstant:
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

        for t1 in unpacked_count_terms:
            # Convert def.neg. heads into explicit terms
            unpacked_head_pool_terms = unpack_head_pool(t1)

            for t2 in unpacked_head_pool_terms:
                # Convert def.neg. body literals into explicit term
                unpacked_body_pool_terms = unpack_body_pool(t2)

                for t3 in unpacked_body_pool_terms:
                    t3 = translate_numeric_string(t3)
                    new_rules += str(t3) + "\n"

                    # Dual statements
                    for dual in get_dual(t3):
                        new_rules += str(dual) + r" % dual" + "\n"
                    # not pred :- -pred DISABLED TO PREVENT INFINITE LOOPS
                    # for explicit_dual in get_explicit_dual(t3):
                    #     new_rules += str(explicit_dual) + r" % dual" + "\n"
                    # :- a, -a
                    for constraint in get_constraints(t3):
                        new_rules += str(constraint) + "\n"

    return "% " + str(term) + "\n" + new_rules