from typing import List, Dict
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from ..utils.chat_model import openai_chat_model
from nl2logic.logic_utils.pysolver.utils import get_hash_head

ASP_RATIONALE_EXAMPLE_PROMPT = \
r"""{{
    'comment': '{comment}',
    'asp': '{asp}'
}},
"""

CONVERT_TO_ASP_PROMPT = \
r"""
ASP syntax and semantics description:
- Arguments can be separated with `;`. Lower  (pooling) Must have same number with args(split with comma).
- Facts are simple rules without body (so that is always true), that can be expressed as a single literal ending with a period.
- Rules follow the following format, with conclusion and reason literals split with `:-` and ending with a period.
- `-a` = "a is false." , `not a` = "a is not proven."
- To denote "or" syntax in the rule body, you might wrap the arguments with `1 <= {{..}}`, and separate the arguments with `;`.

You are given a goal `{curr_goal} to prove. Given a reference document, you will provide a natural language sentence and corresponding ASP code for the goal.
Examples:
"""

FIND_RATIONALE_FROM_DOC_PROMPT = \
r"""You are going to generate a single-sentence fact in 한국어 that unifies with `{curr_goal}` with key `comment`. Capital letters(variables) and _Anon_* unifies with any values.
Then generate the ASP code with key `asp`. All ASP code should include `{curr_goal_head}`.
Format: {{'comment': ..., 'asp': ...}}
Return type: Python Dicts.
"""

def get_asp_and_rationale_from_doc(curr_goal: str, body_text: str, examples: List[Dict] = None) -> List[str]:
    # Set example few-shot prompt
    example_prompt = ChatPromptTemplate.from_template(ASP_RATIONALE_EXAMPLE_PROMPT)
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(CONVERT_TO_ASP_PROMPT),
        few_shot_prompt,
        SystemMessagePromptTemplate.from_template(FIND_RATIONALE_FROM_DOC_PROMPT),
        ("human", "{body_text}")
    ])

    # Run LLMChain
    convert_to_asp_chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    curr_goal_head = get_hash_head(curr_goal)
    result = str(convert_to_asp_chain.run({"curr_goal": curr_goal, "curr_goal_head": curr_goal_head, "body_text": body_text}))
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
