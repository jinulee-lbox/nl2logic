from typing import List
from pygraphviz import *

from nl2logic.logic_utils.pysolver.justification_tree import JustificationTree, JustificationTreeNode
from nl2logic.logic_utils.pysolver.utils import anonymize_vars, get_hash_head, parse_line
from nl2logic.database_utils.queries import db_get_const_information

colors = {
    "law": "#FEF5D4",
    "precedent": "#FFD6AA"
}

def linebreak(string):
    # linebreak heuristics for ASP term.
    new_str = ""
    level = 0 # nested parenthesis level
    for idx, char in enumerate(string):
        # append character
        new_str += char
        if char == "(":
            level += 1
            if level == 1:
                # Initial parenthesis: add newline
                new_str += "\l    "
        elif char == ")":
            level -= 1
            if level == 0:
                # Final parenthesis: peel off last ")" and add newline before it
                new_str = new_str[:-1] + "\l)\l"
        elif char == "," and level == 1:
            new_str += "\l    "
    return new_str


def justification_tree_to_graphviz(tree: JustificationTree):
    graph = AGraph()
    graph.node_attr["style"] = "filled"

    queue: List[JustificationTreeNode] = [(tree.root, 0)]
    nodes = set() # memoization
    while len(queue) > 0:
        curr, color_id = queue.pop(0)
        name = anonymize_vars(curr.repr)
        head = get_hash_head(parse_line(curr.repr + "."))

        # Extract constant
        const = head.replace("not ", "")
        if const.startswith("-"):
            const = const[1:]
        try:
            const_info = db_get_const_information([const])[0]
            is_legal_term = bool(const_info["legal"])
        except:
            is_legal_term = False
        
        # If node is negative and has no child, skip
        # if head.startswith("not ") and len(curr.children) == 0:
        #     continue

        if name not in nodes:
            nodes.add(name)
            graph.add_node(name)
            graph.get_node(name).attr["shape"] = 'box'
            graph.get_node(name).attr["fillcolor"] = colors["law" if is_legal_term else "precedent"]
            graph.get_node(name).attr["label"] = linebreak(name)
        if curr.parent is not None:
            graph.add_edge(anonymize_vars(curr.parent.repr), name)
        for c, c_g in zip(curr.children, curr._children_group):
            queue.append((c, c_g % len(colors)))
    return graph

def graphviz_to_png(graph, filename: str):
    graph.draw(filename, prog="dot")