from typing import *
import logging

from clingo.ast import *
from clingo.control import *
from clingo.symbol import *
from clingo.solving import *

from pysolver.preprocess import preprocess
from pysolver.utils import parse_line, flip_sign
from pysolver import get_proof_tree

def asp_parse_program(terms: List[str]):
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

def asp_reformat_str(term: str, skip_if_fail=False) -> str:
    """Produce reparsible, reformattable string.
    Assumes that
    1) Only `not` and '#[a-z]+` are alphabetical reserved keywords in clingo
    2) Only possible whitespaces are ' ' and '\\n'

    Args:
        term (str): _description_

    Returns:
        str: _description_
    """
    # if term, it ends with a period.
    try:
        if term.strip().endswith('.'):
            result = []
            parse_string(term, result.append)
            return str(result[1])
        # else, add a period, parse, and remove the period.
        else:
            result = []
            parse_string(term + ".", result.append)
            return str(result[1]).replace('.', '').strip()
    except Exception as e:
        if skip_if_fail:
            return term
        else:
            raise RuntimeError("Syntax error while reformatting; use `skip_if_fail` param to skip syntax errors")

def asp_parse_conclusion(conclusions: List[str]):
    success = []
    conc_symbols = []

    for conc in conclusions:
        try:
            # buf = []
            # conc_symbols.append(parse_term(conc, logger=_intercept_message(buf)))
            conc = parse_line(conc + ".").head
            conc_symbols.append(conc)
            success.append({
                'code': 0,
                'msg': "Success"
            })
        except Exception as e:
            success.append({
                'code': 10,
                # 'msg': buf[0] # parse_term의 logger callback 로직에 문제가 있는 듯 함.
                'msg': "Syntax error"
            })
    return conc_symbols, success

def asp_extract_const_list(term: str, exclude_underscore:bool = True):
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

def asp_extract_pred_arg_list(term: str, exclude_underscore:bool = True):
    # Refer to official Potassco guide for details in Transformer.
    pred_arg_list = []
    class ConstantTracker(Transformer):
        def visit_Function(self, node):
            name = node.name
            if not exclude_underscore or not name.startswith("_"):
                for i, arg in enumerate(node.arguments):
                    if arg.ast_type == ASTType.Function and (not exclude_underscore or not arg.name.startswith("_")):
                        pred_arg_list.append((name, i, arg.name))
                        
            self.visit_children(node)
            return node # No change
    
    # parse_string converts string to AST.
    result = []
    # try:
    if True:
        if term.strip().endswith('.'):
            parse_string(term, result.append)
        # else, add a period and parse
        else:
            parse_string(term + ".", result.append)
        result = result[1]  # AST
        unpool_list = result.unpool()
        for u in unpool_list:
            ConstantTracker()(u)
    # except Exception as e:
    #     return []
    return pred_arg_list

def asp_run(program: List[Dict[str, Any]], conc_symbols: List[AST], output_style="html"):
    proofs = []
    flag_success = True
    for conc_symbol in conc_symbols:
        # logging.debug(conc_symbol)
        tree = get_proof_tree(program, conc_symbol)
        if tree:
            tree = str(tree)
            # HTML specific formatting
            if output_style == "html":
                tree = tree.replace("\n", " <br>")
                tree = tree.replace(" ", "&nbsp;")
            proofs.append({
                "conclusion": str(conc_symbol),
                "proved": 1,
                "tree": tree
            })
        else:
            new_conc_symbol = flip_sign(conc_symbol)
            tree = get_proof_tree(program, new_conc_symbol)
            flag_success = False
            if tree:
                tree = str(tree)
                # HTML specific formatting
                if output_style == "html":
                    tree = tree.replace("\n", " <br>")
                    tree = tree.replace(" ", "&nbsp;")
                proofs.append({
                    "conclusion": str(conc_symbol),
                    "proved": 0,
                    "tree": tree
                })
            else:
                tree = get_proof_tree(program, parse_line("#false.").head)
                flag_success = False
                if tree:
                    tree = str(tree)
                    # HTML specific formatting
                    if output_style == "html":
                        tree = tree.replace("\n", " <br>")
                        tree = tree.replace(" ", "&nbsp;")
                    proofs.append({
                        "conclusion": str(conc_symbol),
                        "proved": 0,
                        "tree": tree
                    })
                else:
                    proofs.append({
                        "conclusion": str(conc_symbol),
                        "proved": 0,
                        "tree": "Error"
                    })

    return {
        "satisfactory": "Satisfied" if flag_success else "Unsatisfied",
        "proofs": proofs
    }