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

ASP_RATIONALE_EXAMPLE_PROMPT = \
r"""{{'comment': '{comment}', 'asp': '{asp}'}},
"""

CONVERT_TO_ASP_PROMPT = \
r"""
You are given a goal `{curr_goal_cleansed} to prove. Given a reference document, you will provide a natural language sentence and corresponding prolog code for the goal.
Examples:
"""

FIND_RATIONALE_FROM_DOC_PROMPT = \
r"""comment: '{curr_goal_rationale}'
asp: Prolog code corresponding to the sentence, proving `{curr_goal_cleansed}` or `not {curr_goal_cleansed}`. Use function names only from examples.
Format: {{'comment': '한국어', 'asp': '...'}}
Return type: Python Dicts.
"""

def get_asp_and_rationale_from_doc(curr_goal: AST, curr_goal_cleansed_str: str, body_text: str, examples: List[Dict] = None, error_prompt: str = None) -> List[str]:
    # Set example few-shot prompt
    example_prompt = ChatPromptTemplate.from_template(ASP_RATIONALE_EXAMPLE_PROMPT)
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(CONVERT_TO_ASP_PROMPT),
        few_shot_prompt,
        ("human", "{body_text}"),
        SystemMessagePromptTemplate.from_template(FIND_RATIONALE_FROM_DOC_PROMPT),
    ])
    if error_prompt is not None:
        get_asp_and_rationale_prompt.append(error_prompt)

    # Run LLMChain
    convert_to_asp_chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    curr_goal_head = get_hash_head(curr_goal)
    curr_goal_rationale = get_rationale_from_asp(parse_line(curr_goal_cleansed_str+".").head)
    result = str(convert_to_asp_chain.run({"curr_goal_cleansed": curr_goal_cleansed_str, "curr_goal_head": curr_goal_head, "body_text": body_text, "curr_goal_rationale": curr_goal_rationale}))
    try:
        # Heuristic: if not a python list, add square braces
        if not result.startswith("[") and not result.endswith("]"):
            result = f"[{result}]"
        result = eval(result)
        print(json.dumps(result, ensure_ascii=False, indent=4))
        for r in result:
            r["source"] = "precedent" # add source information
        return result
    except:
        return None # Syntax error, perhaps
