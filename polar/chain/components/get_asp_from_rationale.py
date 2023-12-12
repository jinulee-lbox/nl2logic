from typing import List, Dict
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from nl2logic.logic_utils import asp_extract_const_list
from nl2logic.database_utils import db_get_all_consts
from ..utils.chat_model import openai_chat_model

ASP_RATIONALE_EXAMPLE_PROMPT = \
r"""comment: '{comment}'
asp: ['{asp}']\n
"""

GET_ASP_FROM_RATIONALE_PROMPT = \
r"""You have to convert the natural language sentences into an Answer Set Programming(ASP) rule/fact statement.
"""

GET_ASP_FROM_RATIONALE_DIRECTION_PROMPT = \
r"""Convert the given sentence to ASP program. Generate a python list of single-quoted strings, each a possible conversion, best guess at first.
Goal should unify with {curr_goal_cleansed}.
Format: ['asp1', 'asp2', ...]
Return type: Python List of String.
"""

def get_asp_from_rationale(curr_goal_cleansed: str, rationale: str, examples: List[Dict]) -> List[str]:
    # Extract all constants from examples
    consts = set()
    for ex in examples:
        ex_const = asp_extract_const_list(ex['asp'])
        consts.update(ex_const)
    all_consts = db_get_all_consts()
    for const in all_consts:
        for lu in const["usage"].split(","):
            if lu in rationale:
                consts.update((const['const'], const['nargs']))
                break
    const_text = []
    for const in all_consts:
        if (const['const'], const['nargs']) in consts:
            name, arity, description = const['const'], const['nargs'], const['description']
            if arity > 0:
                name += "("
                name += ", ".join([f"%{i+1}" for i in range(arity)])
                name += ")"
            const_text.append(name + ": " + description)

    # Extract all constants that have any lexical unit inside rationale.

    # Set example few-shot prompt
    example_prompt = ChatPromptTemplate.from_template(ASP_RATIONALE_EXAMPLE_PROMPT)
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(GET_ASP_FROM_RATIONALE_PROMPT),
        ("human", "\n".join(const_text)),
        ("human", "- Make sure to wrap raw strings with appropriate types as in examples.\nExamples:"),
        few_shot_prompt,
        SystemMessagePromptTemplate.from_template(GET_ASP_FROM_RATIONALE_DIRECTION_PROMPT),
        ("human", "comment: {rationale}\nasp:")
    ])

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(chain.run({"curr_goal_cleansed": curr_goal_cleansed, "rationale": rationale})).strip(" \\n")
    
    try:
        if not result.startswith("["):
            result = f"[{result}"
        if not result.endswith("]"):
            result = f"{result}]"
        result = eval(result) # convert string to Python list
        return result
    except:
        return []