from typing import *
import subprocess
import tempfile

from clingo.ast import *
from clingo.control import *
from clingo.symbol import *
from clingo.solving import *

from .scasp_postprocess import *
from .utils import SCASP_PATH

from datetime import datetime

TREE_RECURSION_LIMIT = 2

def get_proof_tree(preprocessed_program: str, conc_symbol: str, recursion_level=0) -> Tuple[str, bool]:
    # Prevent catastrophic recursion
    if recursion_level >= TREE_RECURSION_LIMIT:
        return JustificationTree("query\n  " + conc_symbol), True

    with tempfile.NamedTemporaryFile('w',encoding="UTF-8") as fp:
        # Write program with query to tempfile
        fp.write(preprocessed_program + "\n?- " + conc_symbol + ".\n")
        fp.flush()
        # Run s(CASP)
        complete_process = subprocess.run([SCASP_PATH, fp.name, '--tree', '-n', '0', '--dcc', '--nmr', '--olon'], capture_output=True, text=True)
        raw_result = complete_process.stdout
        raw_error = complete_process.stderr
        if "ERROR" in raw_error:
            raw_error = raw_error.split("\n")
            raw_error = [line for line in raw_error if line.startswith("ERROR")]
            raw_error = "\n".join(raw_error)
            raise RuntimeError(raw_error)
        just_trees = scasp_parse_just_trees(raw_result, debug=False)

        # Parse and merge trees
        if len(just_trees) > 0: 
            merged_justtree = scasp_merge_just_trees(just_trees)
            proved=True
            tree = merged_justtree

            def replace_negheads(node: JustificationTreeNode):
                if node.repr.startswith("not ") and len(node.children) == 0:
                    if node.repr.startswith("not -"):
                        new_repr = node.repr.replace("not -", "not_neg_")
                    else:
                        new_repr = node.repr.replace("not ", "not_")
                    # Ad-hoc solution for detecting `not_a(..) :- ..` FIXME
                    new_repr_pred = new_repr[:new_repr.index('(')]
                    if re.search(rf"{new_repr_pred}\(.*\) :- ", preprocessed_program):
                        # More things to prove
                        subtree, proved = get_proof_tree(preprocessed_program, new_repr, recursion_level+1)
                        # Copy proof tree into original tree
                        if proved:
                            node.children = subtree.root.children
                            node._children_group = subtree.root._children_group
            tree.transform(replace_negheads)
        else:
            proved=False
            tree = JustificationTree("query\n  " + conc_symbol)
        return tree, proved