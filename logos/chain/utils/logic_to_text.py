from clingo.ast import *

from nl2logic.database_utils.queries import db_get_const_information
from nl2logic.logic_utils.api import asp_extract_const_list

def recursive_rule_to_text_conversion(term: AST) -> str:
    consts = asp_extract_const_list(str(term))
    consts = [x[0] for x in consts] # Remove arity, only leave the constant string
    if len(consts) > 0:
        const_info = db_get_const_information(consts)
    else:
        return str(term)
    
    return _recursive_rule_to_text_conversion(term, const_info)

def _recursive_rule_to_text_conversion(term: AST, const_info) -> str:
    # Rule
    if term.ast_type == ASTType.Rule:
        # Recursive conversion
        head_str = _recursive_rule_to_text_conversion(term.head, const_info)
        body_str = [_recursive_rule_to_text_conversion(body, const_info) for body in term.body]
        # Join string
        term_str = head_str
        if len(body_str) > 0:
            term_str = "이고, ".join(body_str) + "이면 " + term_str
        return term_str

    # Literal -> remove signs (-, not) and extract inner literal
    if term.ast_type == ASTType.Literal:
        is_not = term.sign == Sign.Negation
        is_classicneg = (
            term.atom.ast_type == ASTType.SymbolicAtom and
            term.atom.symbol.ast_type == ASTType.UnaryOperation and
            term.atom.symbol.operator_type == UnaryOperator.Minus
        )
        if is_not and is_classicneg:
            core = term.atom.symbol.argument
            tail = "이 아님을 증명할 수 없다."
        elif is_not and not is_classicneg:
            core = term.atom.symbol
            tail = "을 증명할 수 없다."
        elif not is_not and is_classicneg:
            core = term.atom.symbol.argument
            tail = "이 아니다."
        else:
            core = term.atom.symbol
            tail = ""
        return _recursive_rule_to_text_conversion(core, const_info) + tail
        
    if term.ast_type == ASTType.BinaryOperation:
        print(term)
        return str(term)
    
    if term.ast_type == ASTType.Function:
        fn_name = term.name
        data = [x for x in const_info if x["const"] == fn_name][0] # Extract const information
        arguments = [_recursive_rule_to_text_conversion(x, const_info) for x in term.arguments]
        frame = data["description"]
        for i in range(len(arguments)):
            # Frame format: %1이 %2를 %3에서, %4부터 %5까지 %6 경로로 몰았다. 
            frame = frame.replace(f"%{i+1}", arguments[i])
        return frame
    
    if term.ast_type == ASTType.Pool:
        arguments_str = [_recursive_rule_to_text_conversion(x, const_info) for x in term.arguments]
        return "/".join(arguments_str)
    if term.ast_type == ASTType.SymbolicTerm or term.ast_type == ASTType.Variable:
        term_str = str(term)
        if term_str.startswith('"') and term_str.endswith('"'):
            term_str.strip('"')
        return term_str

    raise ValueError("No matching type")
