import networkx as nx

from ..database_utils.queries import db_get_entity_relation, db_get_all_consts

def get_is_a_relation() -> nx.DiGraph:
    graph = nx.DiGraph()

    # Add entity with hierarchy
    edges_raw = db_get_entity_relation()
    consts = db_get_all_consts()
    edge_tuples = [(edge["const2"], edge["const1"]) for edge in edges_raw] # parent -> child
    graph.add_edges_from(edge_tuples)

    # Gather nodes that do not have explicit parent
    entities_with_no_incoming_edges = [node for node in graph.nodes() if graph.in_degree(node) == 0]
    # Add nodes that did not appear on relations
    entities_with_no_incoming_edges += [const["const"] for const in consts if const["source"] == "entity" and not graph.has_node(const["const"])]
    # Add a dummy root to these nodes
    graph.add_edges_from([("entity", node) for node in entities_with_no_incoming_edges])
    # Add useful properties
    for node in [pred for pred in consts if pred["source"] == "entity"]:
        graph.nodes[node["const"]]["description"] = node["description"]
        graph.nodes[node["const"]]["usage"] = node["usage"]

    # Add predicate
    predicates = [pred for pred in consts if pred["source"] == "predicate"]
    edge_tuples = [(pred["const"], "predicate") for pred in predicates] # parent -> child
    graph.add_edges_from(edge_tuples)
    for pred in predicates:
        graph.nodes[pred["const"]]["description"] = pred["description"]
        graph.nodes[pred["const"]]["usage"] = pred["usage"]

    # Add a dummy root for predicate and entity
    graph.add_edges_from([('predicate', '_'), ('entity', '_')])

    return graph

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from networkx.drawing.nx_agraph import graphviz_layout
    G = get_is_a_relation()
    pos=graphviz_layout(G, prog='dot')
    nx.draw(G, pos, with_labels=True, arrows=False)
    plt.savefig("test.png")