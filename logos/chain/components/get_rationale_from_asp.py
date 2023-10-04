from typing import List, Dict, Tuple
import re

from clingo.ast import AST
from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from nl2logic.database_utils.queries import db_get_const_information
from nl2logic.logic_utils.api import asp_extract_const_list

from ..utils.chat_model import openai_chat_model

GET_RATIONALE_FROM_ASP_PROMPT = \
r"""너는 수식을 규칙에 따라 자연스러운 한국어로 풀이해주는 AI야.
대문자는 변수 기호인데, 같은 변수는 서로 같은 대상을 지칭해. 
`:-`가 들어있으면 뒤에 나오는 것들이 원인, 앞에 나오는 게 결론이야.
`a :- b, c, d` 는 "b이고, c이고, d이면 a이다."라고 출력하는 것이야.
`_`는 아무 뜻도 없으니 답에 절대 들어가서는 안돼.
`-a`는 "a가 아니다." 라는 뜻이며, `not a`는 "a가 증명되지 않는다." 라는 뜻이야.
같은 알파벳은 같은 대상을 의미해.
"""
GET_RATIONALE_FROM_ASP_DIRECTION_PROMPT = \
r"""frame 정보와 예시들을 참고해서, 주어진 문장에서 함수에 나타나지 않은 정보는 제외하고 새로운 문장을 만들어줘.
"""

def get_rationale_from_asp(goal: AST, original_nl_description, examples) -> str:
    consts = list(set(asp_extract_const_list(goal)))
    if len(consts) > 0:
        const_info = db_get_const_information(consts)
        sorted(const_info, key = lambda x: consts.index(x["const"]))
    else:
        const_info = []

    ontology_description = []
    for const in const_info:
        description = const['const']
        if const['nargs'] > 0:
            # parenthesis if nargs>0
            description += "("
            description += ",".join([f"%{i+1}" for i in range(const['nargs'])])
            description += ")"
        description += ": " + const["description"]
        ontology_description.append({
            "description": f"{description}"
        })

    # Set example few-shot prompt
    ontology_prompt = ChatPromptTemplate.from_messages(
        [('human', '{description}')]
    )
    ontology_description_prompt = FewShotChatMessagePromptTemplate(
        examples=ontology_description,
        example_prompt=ontology_prompt
    )

    example_prompt = ChatPromptTemplate.from_messages(
        [("human", "{asp}"),
         ("ai", "{comment}")]
    )
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(GET_RATIONALE_FROM_ASP_PROMPT),
        ontology_description_prompt,
        SystemMessagePromptTemplate.from_template(GET_RATIONALE_FROM_ASP_DIRECTION_PROMPT),
        few_shot_prompt,
        ("human", "주어진 문장: {comment}"),
        ("human", "수식: {goal}")
    ])

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    goal = re.sub(r"([,( ])(_*[A-Z][A-Za-z_0-9]*)(?=[,)]| [+\-*/%><=!])", "\g<1>_", str(goal)) # Remove variables
    result = str(chain.run({"goal": goal, "comment": original_nl_description}))
    try:
        return result
    except:
        return None # Syntax error, perhaps