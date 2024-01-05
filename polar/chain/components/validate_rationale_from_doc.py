from typing import List, Dict, Tuple
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from ..utils.chat_model import openai_chat_model

def validate_rationale_from_document(natural_language_goal, body_text, context) -> Tuple[bool, str]:
    # Set example few-shot prompt
    prompt = context.prompt_data['validate_description_from_document']
    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(prompt),
        ("human", "Document:\n{body_text}"),
        ("human", "Sentence: {goal}"),
    ])

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(chain.run({"goal": natural_language_goal, "body_text": body_text}))
    if "no." in result.lower():
        return False, result.replace("No.", "").replace("no.", "").strip()
    else:
        return True, result.replace("Yes.", "").replace("yes.", "").strip()