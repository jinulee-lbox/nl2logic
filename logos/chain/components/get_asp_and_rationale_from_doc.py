from typing import List, Dict
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from ..utils.chat_model import openai_chat_model

ASP_RATIONALE_EXAMPLE_PROMPT = \
r"""{{
    "comment": {comment},
    "asp": {asp}
}}
"""

CONVERT_TO_ASP_PROMPT = \
r"""You are given a goal `{curr_goal} to prove. Given a reference document, you will provide a natural language sentence and corresponding ASP code for the goal.
Examples:
"""

FIND_RATIONALE_FROM_DOC_PROMPT = \
r"""You are going to generate a fact in 한국어 that proves `{curr_goal}`, with key 'comment'.
Then generate the ASP code with key `asp`. All ASP code should start with `{curr_goal}`. Use every information that can be found in the document to fill in the arguments.
Return type: JSON List of Dicts, with maximum three elements.
"""

def get_asp_and_rationale_from_doc(curr_goal: str, body_text: str, examples: List[Dict] = None) -> List[str]:
    if examples is not None:
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
    else:
        get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(CONVERT_TO_ASP_PROMPT),
            SystemMessagePromptTemplate.from_template(FIND_RATIONALE_FROM_DOC_PROMPT),
            ("human", "{body_text}")
        ])

    # Run LLMChain
    convert_to_asp_chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(convert_to_asp_chain.run({"curr_goal": curr_goal, "body_text": body_text}))
    try:
        result = json.loads(result)
        # print(json.dumps(result, ensure_ascii=False, indent=4))
        if isinstance(result, dict):
            result = [result] # Convert dict to list
        for r in result:
            r["source"] = "precedent" # add source information
        return result
    except:
        return None # Syntax error, perhaps
