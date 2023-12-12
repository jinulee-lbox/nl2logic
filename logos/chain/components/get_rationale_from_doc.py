from typing import List, Dict
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from clingo.ast import AST

from ..utils.chat_model import openai_chat_model
from .get_rationale_from_asp import get_rationale_from_asp
from pysolver.utils import get_hash_head, parse_line

RATIONALE_EXAMPLE_PROMPT = \
r"""'{comment}',
"""

CONVERT_TO_ASP_PROMPT = \
r"""You are finding a proof for {curr_goal_text} with fixed format.
Format examples:
"""

FIND_RATIONALE_FROM_DOC_PROMPT = \
r"""Given the document, find a valid proof for {curr_goal_text} referring to the document.
Return type: Python List of String.
"""

def get_rationale_from_doc(curr_goal_text: str, body_text: str, examples: List[Dict] = None) -> List[str]:
    # Set example few-shot prompt
    example_prompt = ChatPromptTemplate.from_template(RATIONALE_EXAMPLE_PROMPT)
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(CONVERT_TO_ASP_PROMPT),
        few_shot_prompt,
        SystemMessagePromptTemplate.from_template(FIND_RATIONALE_FROM_DOC_PROMPT),
        ("human", "{body_text}"),
    ])

    # Run LLMChain
    convert_to_asp_chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(convert_to_asp_chain.run({"curr_goal_text": curr_goal_text, "body_text": body_text})).strip(" \\n")
    try:
        # Heuristic: if not a python list, add square braces
        if not result.startswith("["):
            result = f"[{result}"
        if not result.endswith("]"):
            result = f"{result}]"
        result = eval(result)
        return result
    except:
        return None # Syntax error, perhaps
