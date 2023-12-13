from clingo.ast import AST
from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
)

from ..utils.statement_to_text import statement_to_text
from ..utils.chat_model import openai_chat_model

GET_RATIONALE_FROM_ASP_PROMPT = \
r"""Fix the following sentence into a grammatical sentence without removing and changing any nouns, verbs and adjectives. Copy if already correct. Skip underscore(_).
"""
GET_RATIONALE_FROM_ASP_PROMPT_KOREAN = \
r"""다음 문장을 하나의 문장으로 다듬고, 조사나 어순, 호응이 어색한 부분을 수정하고, 중복된 단어들을 제거해서 읽기 편하게 만들어야 한다.
x나 _가 들어간 구는 건너뛰어라.
"""

def get_rationale_from_asp(goal: AST, polar_context) -> str:    
    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(GET_RATIONALE_FROM_ASP_PROMPT),
        ("human", "{goal_str}")
    ])
    goal_str = statement_to_text(goal, polar_context)

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result_str = str(chain.run({"goal_str": goal_str}))
    
    return result_str