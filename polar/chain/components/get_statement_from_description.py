from typing import List, Dict
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from pysolver.utils import extract_const_list, parse_line
from ..utils.chat_model import openai_chat_model
from ..utils.context import PolarContext

ASP_RATIONALE_EXAMPLE_PROMPT = \
r"""description: '{description}'
statement: ['{statement}']\n
"""

def get_statement_from_description(curr_goal_cleansed: str, rationale: str, examples: List[Dict], context: PolarContext) -> List[str]:
    prompt = context.prompt_data['get_statement_from_description']
    # Set example few-shot prompt
    example_prompt = ChatPromptTemplate.from_template(ASP_RATIONALE_EXAMPLE_PROMPT)
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )
    # Extract all constants that have any lexical unit inside rationale.
    example_prompt = ChatPromptTemplate.from_template(ASP_RATIONALE_EXAMPLE_PROMPT)

    if context.ontology_data is not None:
        # Extract all constants from examples
        consts = set()
        for ex in examples:
            ex_const = extract_const_list(parse_line(ex['statement']))
            consts.update(ex_const)
        all_consts = context.ontology_data
        for const in all_consts:
            for lu in const["lexical_unit"]:
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
        get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(prompt),
            few_shot_prompt,
            ("human", "\n".join(const_text)),
            ("human", "description: {rationale}\nstatement:")
        ])  
    else:
        get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(prompt),
            few_shot_prompt,
            ("human", "description: {rationale}\nstatement:")
        ])


    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(chain.run({"curr_goal_cleansed": curr_goal_cleansed, "description": rationale})).strip(" \\n")
    
    try:
        # Heuristic: if not a python list, add square braces
        if not result.startswith("["):
            result = f"[{result}"
        if not result.endswith("]"):
            result = f"{result}]"
        # Heuristic: if the model adds integer division, convert to normal division.
        if "//" in result:
            result = result.replace("//", "/")
        result = eval(result) # convert string to Python list
        return result
    except:
        return []