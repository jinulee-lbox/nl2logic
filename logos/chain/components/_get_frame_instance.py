from typing import List, Dict, Tuple
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from nl2logic.database_utils import db_get_const_information

from ..utils.chat_model import openai_chat_model

VALIDATE_RATIONALE_FROM_DOC_PROMPT = \
r"""You are going to perform frame detection, like FrameNet. Refer to the description of the frame.
"""

VALIDATE_RATIONALE_FROM_DOC_INSTRUCTION_PROMPT = \
r"""From the document, find every instances of the given frame as nested Python list of arguments.
[[arg1, ..., arg{nargs}], [arg1', ..., arg{nargs}'], ...]
"""

def get_frame_instance(const: str, body_text, examples = None, fixed_args = None) -> List[List[str]]:
    # Set example few-shot prompt
    args = db_get_const_information([const])[0]
    args["body_text"] = body_text

    messages = [
        SystemMessagePromptTemplate.from_template(VALIDATE_RATIONALE_FROM_DOC_PROMPT),
        ("human", "Frame: {const}\nDescription: {description}\nArgument count: {nargs}"),
    ]
    if examples:
        messages.append(("human", "Examples:\n{examples}"))
    messages.extend([
        ("human", "Document:\n{body_text}"),
        SystemMessagePromptTemplate.from_template(VALIDATE_RATIONALE_FROM_DOC_INSTRUCTION_PROMPT.format(nargs=args["nargs"]))
    ])

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages(messages)

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = eval(str(chain.run(args)))
    print(result)