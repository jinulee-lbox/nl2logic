SPLIT_TO_SENT_PROMPT = r"""
Split the following Korean precedent document into a set of facts and rules.
Facts should have a single semantic verb frame included.
Facts are likely to follow the format "A는 B와 C에서 ... 이다/했다."
Rules should include a cause/effect or postulate/conclusion relationship.
Rules are likely to follow the format "A이고 B이거나 C라면 ... D이다."
If any frame elements like agent, theme, instrument, location, path, .. are missing or presented as pronouns, you must explicitly specify the surface form of the missing element.
Return a JSON list with string of Korean sentences, with all rules and facts you can identify.
"""

CONVERT_TO_ASP_PROMPT = r"""
You have to convert the natural sentences into an Answer Set Programming(ASP) program.
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

You will be continuously given a single sentence from a legal document, and have to reply in single Rule or a Fact.
Constant values(unquoted, camelCased words starting with lower case) and their arity(number of arguments) should follow the given example, while string literals are free in format.
"""