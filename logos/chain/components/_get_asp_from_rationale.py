from typing import List, Dict
import json

from langchain import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from ..utils.chat_model import openai_chat_model

GET_ASP_FROM_RATIONALE_PROMPT = \
r"""You have to convert the natural language sentences into an Answer Set Programming(ASP) program.
- Constants, like verbs and nouns specified, start with lower case, while Variables start with upper case letters.
- Positive Literals, the basic block of ASP programming, are written as nested functions.
    Function names are always constant, while arguments can be other functions, constants, variables, numbers and double-quoted strings.
- Strictly Negated Literals mean that 'It is proven false', and is annotated with prefix `-` (hyphen).
- You can use pooling syntax, by connecting the function argument tuples with `;`, when different argument tuples all hold together.
- Facts are simple rules without body (so that is always true), that can be expressed as a single literal ending with a period.
`factLiteral.`
- Rules follow the following format, with conclusion and reason literals split with `:-` and ending with a period.
`conclusionLiteral(..) :- reason1Literal(..), reason2Literal(..), .., reasonNLiteral(..).`
- Both conclusion and reason literals can be classically negated, meaning that 'It cannot be proven true', with the prefix 'not ' attached.
  Strictly negated literals can be also classically negated, meaining that "It cannot be proven false" respect to the corresponding positive literal.
- To denote "or" syntax in the rule body, you might wrap the arguments with `1 <= {{..}}`, and separate the arguments with `;`.
- If the text does not contain any information of a given argument, you might write `_` (underscore) for rules, and `x` for facts.
"""

GET_ASP_FROM_RATIONALE_DIRECTION_PROMPT = \
r"""Convert the given sentence to ASP program. Generate a python list of single-quoted strings, each a possible conversion, best guess at first.
"""

def get_asp_from_rationale(curr_goal: str, rationale: str, examples: List[Dict]) -> List[str]:
    # Set example few-shot prompt
    example_prompt = ChatPromptTemplate.from_messages(
        [('human', '{comment}'), ('ai', '{asp}')]
    )
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )

    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(GET_ASP_FROM_RATIONALE_PROMPT),
        few_shot_prompt,
        SystemMessagePromptTemplate.from_template(GET_ASP_FROM_RATIONALE_DIRECTION_PROMPT),
        ("human", "{rationale}")
    ])

    # Run LLMChain
    chain = LLMChain(llm=openai_chat_model(), prompt=get_asp_and_rationale_prompt)
    result = str(chain.run({"curr_goal": curr_goal, "rationale": rationale}))
    try:
        result = eval(result)
        return result
    except:
        return None # Syntax error, perhaps