from .parse import parse_program, parse_goal
from .solve import solve
from .preprocess import preprocess
from .justification_tree import JustificationTree

# program = """
# a(X, x) :- b(X).
# not a(X, x) :- not b(X).
# a(X, y) :- c(X).
# not a(X, y) :- not c(X).
# b(v).
# aaa(X) :- not a(X, Y).
# not aaa(X) :- a(X, Y).
# """
# goal = "not aaa(v)"
# goal = "aaa(v)"

# program = """
# a(X) :- b(X).
# a(X) :- c(X).
# b(v).
# c(v).
# """
# goal = "a(v)"

# program = """
# a(X) :- b(X), c(X).
# c(X) :- d(X).
# b(X) :- c(X).
# d(v).
# """
# goal = "a(v)"

# program = """
# -a(X) :- b(X, Y), c(Y, Z).
# not -a(X) :- not b(X, Y).
# not -a(X) :- b(X, Y), not c(Y, Z).
# b(p, q).
# c(p, r).
# """
# goal = "not -a(p)"
# goal = "-a(p)"

program = """
b(X) :- not a(X, _, _), e(Y).
a(X, hello, world) :- c(X).
a(X, see, ya) :- d(X).
c(p).
e(anything).
"""
goal = "b(q)."

# program = """
# a :- b(X), c(Y), X > Y.
# b(1).
# c(2).
# b(3).
# """
# goal = "not a"

##### MAIN #####
# Preprocess
lines = program.split("\n")
preprocessed = ""
for line in lines:
    if line.strip() == "": continue
    preprocessed += preprocess(line)
print(preprocessed)
# Run proof
rule_table, _ = parse_program(preprocessed)
print([str(x) for x in rule_table["b"]])
goal = parse_goal(goal)
result = solve(goal, rule_table)
print("[PROVED!!!]" if result else "[FAILED!!!]")
print(len(result))
for i, stack in enumerate(result):
    print("Solution", i+1)
    print(JustificationTree(result[i]))