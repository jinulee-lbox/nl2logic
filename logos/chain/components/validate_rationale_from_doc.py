from typing import List, Dict, Tuple
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from ..utils.chat_model import openai_chat_model

VALIDATE_RATIONALE_FROM_DOC_PROMPT = \
r"""You are a legal expert. Your goal is to read the document given, and judge if the sentence is true or at least not contradictory to the document.
"""

VALIDATE_RATIONALE_FROM_DOC_DIRECTION_PROMPT = \
r"""Answer with 'Yes.' or 'No.'. Can this sentence be "inferred" without contradiction?.
"""

def validate_rationale_from_doc(natural_language_goal, body_text) -> Tuple[str, str]:
    # Set example few-shot prompt

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(VALIDATE_RATIONALE_FROM_DOC_PROMPT),
        ("human", "Document:\n{body_text}"),
        SystemMessagePromptTemplate.from_template(VALIDATE_RATIONALE_FROM_DOC_DIRECTION_PROMPT),
        ("human", "Sentence: {goal}")
    ])

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(chain.run({"goal": natural_language_goal, "body_text": body_text}))
    if "no." in result.lower():
        return False
    else:
        return True