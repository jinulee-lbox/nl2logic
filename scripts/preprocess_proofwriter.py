import json
from tqdm import tqdm
from ast import literal_eval
import re
from random import shuffle

from nl2logic.logic_utils import asp_run, asp_parse_conclusion

DIR = "raw_data/proofwriter/proofwriter-dataset-V2020.12.3/CWA/NatLang/meta-test.jsonl"


def parse_triple(text: str):
    text = text.replace(" ", ", ")
    subj, verb, obj, sign = literal_eval(text)
    # ProofWriter Only
    assert verb == "is"
    return f'{"" if sign == "+" else "not "}{verb}({subj}, {obj})'

def parse_rule(text: str):
    text = text[1:-1] # remove meaningless outer parens

    body, head = text.split(" -> ")
    # body
    body = body[2:-2]
    body = body.split(") (")
    body = [f"({x})" for x in body]
    body = [parse_triple(x) for x in body]
    # head
    head = parse_triple(head)
    result = f"{head} :- {', '.join(body)}."
    return result

results = []
with open(DIR, "r") as file:
    for idx, line in tqdm(enumerate(file.readlines())):
        data = json.loads(line)

        triples = {}; rules = {}
        for tname, t in data['triples'].items():
            triple = parse_triple(t['representation']).lower() + "."
            triples[tname] = {"asp": triple, "comment": t['text']}
            # print(tname, ":", t['text'])
            # print(" ", triple)
        for rname, r in data['rules'].items():
            rule = parse_rule(r['representation']).lower().replace("someone", "X")
            # print(rname, ":", r['text'])
            # print(" ", rule)
            rules[rname] = {"asp": rule, "comment": r['text']}
        
        # Provable goals
        for q in data["questions"].values():
            goal = parse_triple(q['representation']).lower()
            prgm = []
            
            if ("not" in q['question']) != q["answer"]:
                # "A is B" is true, or "A is not B" is False
                triple_list = set(re.findall("triple[0-9]+", q["proofs"]))
                for tname in triple_list:
                    prgm.append(triples[tname])
                rules_list = set(re.findall("rule[0-9]+", q["proofs"]))
                for rname in rules_list:
                    prgm.append(rules[rname])

                # Test using solver
                if "not" in q["question"]:
                    new_goal = goal.replace("not ", "")
                else:
                    new_goal = goal
                asp_run_result = asp_run(prgm, asp_parse_conclusion([new_goal])[0], output_style=None)
                if asp_run_result["satisfactory"] != "Satisfied":
                    print(json.dumps(q, indent=4))
                    print(json.dumps(prgm, indent=4))
                    print(json.dumps(asp_run_result, indent=4))
                    exit(0)
            results.append({
                "id": idx,
                "body_text": data['theory'],
                "rule_names": [],
                "goal": goal,
                "label": q["answer"], # == False
                "program": prgm
            })
# Sample only 300 examples
shuffle(results)
results = results[:300]
with open("data/proofwriter/test_data.json", "w") as file:
    json.dump(results, file, indent=4)