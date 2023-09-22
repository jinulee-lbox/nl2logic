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

# CONVERT_TO_ASP_PROMPT = \
# r"""You have to convert the natural language sentences into an Answer Set Programming(ASP) program.
# - Constants, like verbs and nouns specified, start with lower case, while Variables start with upper case letters.
# - Positive Literals, the basic block of ASP programming, are written as nested functions.
#     Function names are always constant, while arguments can be other functions, constants, variables, numbers and double-quoted strings.
# - Strictly Negated Literals mean that 'It is proven false', and is annotated with prefix `-` (hyphen).
# - You can use pooling syntax, by connecting the function argument tuples with `;`, when different argument tuples all hold together.
# - Facts are simple rules without body (so that is always true), that can be expressed as a single literal ending with a period.
# `factLiteral.`
# - Rules follow the following format, with conclusion and reason literals split with `:-` and ending with a period.
# `conclusionLiteral(..) :- reason1Literal(..), reason2Literal(..), .., reasonNLiteral(..).`
# - Both conclusion and reason literals can be classically negated, meaning that 'It cannot be proven true', with the prefix 'not ' attached.
#   Strictly negated literals can be also classically negated, meaining that "It cannot be proven false" respect to the corresponding positive literal.
# - To denote "or" syntax in the rule body, you might wrap the arguments with `1 <= {{..}}`, and separate the arguments with `;`.
# - If the text does not contain any information of a given argument, you might write `_` (underscore) for rules, and `x` for facts.

# Refer to following examples for how sentences are converted to ASP code.
# """
CONVERT_TO_ASP_PROMPT = \
r"""You have to convert the natural language sentences into an Answer Set Programming(ASP) program.
Refer to following examples for how sentences are converted to ASP code.
"""

FIND_RATIONALE_FROM_DOC_PROMPT = \
r"""Now, you are going to find a rationale that support goal `{curr_goal}` from the given document.
First extract the sentence that might prove the given goal from the document with key `comment`. Such sentences should appear in the text, contain exact information for `{curr_goal}`and not overlap with each other.
Then generate the ASP code with key `asp`. ASP head should unify with `{curr_goal}`.
Return type: JSON list nested with dict, with keys `comment` and `asp`. If cannot prove anything, return empty list.
"""

def get_asp_and_rationale_with_examples(curr_goal: str, body_text: str, examples: List[Dict]) -> List[str]:
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

    # Run LLMChain
    convert_to_asp_chain = LLMChain(llm=openai_chat_model, prompt=get_asp_and_rationale_prompt)
    result = str(convert_to_asp_chain.run({"curr_goal": curr_goal, "body_text": body_text}))
    try:
        result = json.loads(result)
        print(json.dumps(result, ensure_ascii=False, indent=4))
        return result
    except:
        return None # Syntax error, perhaps

def get_asp_and_rationale_without_examples(curr_goal: str, body_text: str) -> List[str]:
    get_asp_and_rationale_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(CONVERT_TO_ASP_PROMPT),
        SystemMessagePromptTemplate.from_template(FIND_RATIONALE_FROM_DOC_PROMPT),
        ("human", "{body_text}")
    ])

    # Run LLMChain
    convert_to_asp_chain = LLMChain(llm=openai_chat_model, prompt=get_asp_and_rationale_prompt)
    result = str(convert_to_asp_chain.run({"curr_goal": curr_goal, "body_text": body_text}))
    try:
        result = json.loads(result)
        return result
    except:
        return None # Syntax error, perhaps