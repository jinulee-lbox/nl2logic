from clingo.ast import *

from nl2logic.database_utils import db_get_const_information
from nl2logic.logic_utils import asp_extract_const_list

def statement_to_text(term: AST, polar_context) -> str:
    consts = asp_extract_const_list(str(term))
    consts = [x[0] for x in consts] # Remove arity, only leave the constant string
    if len(consts) == 0:
        return str(term)
    return _recursive_rule_to_text_conversion(term, polar_context.ontology_data)

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
        is_boolconst_true = (
            term.atom.ast_type == ASTType.BooleanConstant and
            term.atom.value
        )
        is_boolconst_false = (
            term.atom.ast_type == ASTType.BooleanConstant and
            not term.atom.value
        )
        is_comparison = term.atom.ast_type == ASTType.Comparison
        is_symbolicatom = term.atom.ast_type == ASTType.SymbolicAtom
        is_classicneg = (
            term.atom.ast_type == ASTType.SymbolicAtom and
            term.atom.symbol.ast_type == ASTType.UnaryOperation and
            term.atom.symbol.operator_type == UnaryOperator.Minus
        )
        if is_boolconst_true:
            return ""
        elif is_boolconst_false:
            return "동시에 성립할 수 없다." # in ordinary cases, boolconst_false only appears in the constraint head position.
        elif is_comparison:
            return str(term)
 
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
            try:
                core = term.atom.symbol
            except:
                print(term, term.ast_type)
                return ""
            tail = ""
        return _recursive_rule_to_text_conversion(core, const_info) + tail
        
    if term.ast_type == ASTType.BinaryOperation:
        print(term)
        return str(term)
    if term.ast_type == ASTType.UnaryOperation:
        if term.operator_type != UnaryOperator.Minus:
            raise ValueError("No other AST.UnaryOperator than Minus is supported")
        core = term.argument
        tail = "이 아니다."
        return _recursive_rule_to_text_conversion(core, const_info) + tail
    
    if term.ast_type == ASTType.Function:
        fn_name = term.name
        try:
            data = [x for x in const_info if x["const"] == fn_name][0] # Extract const information
        except IndexError: # Customly defined constants (related to exclude_underscore = True in asp_extract_const_list())
            arity = len(term.arguments)
            if arity > 0:
                description = ", ".join([f'%{i}'for i in range(arity)])
                description += f"는 {fn_name} 을 만족한다."
            else:
                description = f"{fn_name} 이다."
            data = {"description": description}
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

    raise ValueError(f"No matching type: {term.ast_type} for {term}")

if __name__ == "__main__":
    l = []
    parse_string("xxx(-isEffective(driversLicense)) :- -hello(X).", l.append)
    statement_to_text(l[1])