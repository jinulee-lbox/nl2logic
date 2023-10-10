from typing import List, Dict, Tuple
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
)
import networkx as nx

from ..utils.chat_model import openai_chat_model
from nl2logic.ontology_utils.is_a import get_is_a_relation

NAMED_ENTITY_RECOGNITION_PROMPT = """You are going to perform multi-class named entity recognition.
Classes:
{}"""
NAMED_ENTITY_RECOGNITION_INSTRUCTION_PROMPT = """
Instructions:
Each entities recognized should not overlap in span. Only include identifiers, not prefixes. For example: "A" instead of "피고인 A".
Format: JSON list of dicts, [{{"category": ..., "name": ...}}, ...]"""

def get_named_entity_recognition(body_text) -> Tuple[str, str]:
    # Get all entities
    entity_graph = get_is_a_relation()
    entity_list = ""
    for name in nx.descendants(entity_graph, "entity"):
        data = entity_graph.nodes[name]
        if "description" in data.keys():
            entity_list += name + ": " + data["description"].replace("%1", "X") + "\n"

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(NAMED_ENTITY_RECOGNITION_PROMPT.format(entity_list)),
        ("human", "Document:\n{body_text}"),
        SystemMessagePromptTemplate.from_template(NAMED_ENTITY_RECOGNITION_INSTRUCTION_PROMPT),
    ])

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(chain.run({"body_text": body_text}))
    print(result)
    result = json.loads(result)

    # Check if valid category
    result = [r for r in result if entity_graph.has_node(r["category"])]
    # Heuristics for postprocesing FIXME
    EXCLUDE_LIST = set([("defendant", "피고인")])
    result = [r for r in result if (r["category"], r["name"]) not in EXCLUDE_LIST]
    
    # Expand category to superconcepts
    for r in result:
        category = r["category"]
        for pred in entity_graph.predecessors(category):
            if pred != "entity":
                result.append({"category": pred, "name": r["name"]})
    return result