from typing import List, Dict, Tuple
import re

from clingo.ast import AST
from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
)

from ..utils.logic_to_text import recursive_rule_to_text_conversion

from ..utils.chat_model import openai_chat_model

GET_RATIONALE_FROM_ASP_PROMPT = \
r"""당신은 판사이다. 다음 문장을 하나의 문장으로 다듬고, 조사나 어순, 호응이 어색한 부분을 수정하고, 중복된 단어들을 제거해서 읽기 편하게 만들어야 한다.
x나 _가 들어간 구는 건너뛰어라.
"""
MERGE_WITH_RETRIEVED_SENT_PROMPT = \
r"""주어진 문장을 더 읽기 편하게 다듬을 것.
"""

def get_rationale_from_asp(goal: AST) -> str:    
    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(GET_RATIONALE_FROM_ASP_PROMPT),
        ("human", "{goal_str}")
    ])
    goal_str = recursive_rule_to_text_conversion(goal)

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result_str = str(chain.run({"goal_str": goal_str}))

    # merge_with_retrieved_sent_prompt = ChatPromptTemplate.from_messages([
    #     ("human", "{comment}\n" + MERGE_WITH_RETRIEVED_SENT_PROMPT),
    #     ("human", "{result_str}"),
    # ])
    # chain = LLMChain(llm=openai_chat_model(), prompt=merge_with_retrieved_sent_prompt)
    # result = str(chain.run({"goal_str": goal_str, "result_str": result_str, "comment": comment}))
    
    return result_str