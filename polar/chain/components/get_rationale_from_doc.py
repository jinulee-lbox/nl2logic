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
from ..utils.context import PolarContext
from pysolver.utils import get_hash_head, parse_line

RATIONALE_EXAMPLE_PROMPT = \
r"""{description}
"""

def get_description_from_document(curr_goal_text: str, body_text: str, examples: List[Dict], context: PolarContext) -> List[str]:
    # Set example few-shot prompt
    example_prompt = ChatPromptTemplate.from_template(RATIONALE_EXAMPLE_PROMPT)
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )
    prompt = context.prompt_data['get_description_from_document']
    use_fewshot_prompt = context.config.get_dsecription_from_statement_few_shot
    if use_fewshot_prompt:
        get_description_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(prompt),
            few_shot_prompt,
            ("human", "{body_text}"),
        ])
    else:
        get_description_prompt = ChatPromptTemplate.from_messages([
            few_shot_prompt,
            ("human", "{body_text}"),
        ])

    # Run LLMChain
    convert_to_asp_chain = LLMChain(llm=openai_chat_model(), prompt=get_description_prompt)
    result = str(convert_to_asp_chain.run({"curr_goal_text": curr_goal_text, "body_text": body_text})).strip(" \\n")
    print(result)
    try:
        return [x.strip() for x in result.split("\n")]
    except:
        return None # Syntax error, perhaps
