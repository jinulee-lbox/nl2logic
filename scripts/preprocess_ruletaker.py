import json
from tqdm import tqdm
from ast import literal_eval
import re
from random import shuffle

from nl2logic.logic_utils import asp_run, asp_parse_conclusion

def parse_triple(text: str):
    # text = text.replace(" ", ", ")
    text = re.sub('" "', '", "', text)
    subj, verb, obj, sign = literal_eval(text)
    subj = subj.replace(" ", "_")
    obj = obj.replace(" ", "_")
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

for DEPTH in [1, 3, 5]:
    print("DEPTH:", DEPTH)
    DIR = f"raw_data/proofwriter/proofwriter-dataset-V2020.12.3/CWA/depth-{DEPTH}/meta-test.jsonl"
    results = []
    with open(DIR, "r") as file:
        cnt = 0
        miss_cnt = 0
        for idx, line in tqdm(enumerate(file.readlines())):
            data = json.loads(line)

            triples = {}; rules = {}
            for tname, t in data['triples'].items():
                triple = parse_triple(t['representation']).lower() + "."
                triples[tname] = {"asp": triple, "comment": t['text']}
                # print(tname, ":", t['text'])
                # print(" ", triple)
            for rname, r in data['rules'].items():
                rule = parse_rule(r['representation']).lower().replace("someone", "X").replace("something", "X")
                # print(rname, ":", r['text'])
                # print(" ", rule)
                rules[rname] = {"asp": rule, "comment": r['text']}
            
            # Provable goals
            for q in data["questions"].values():
                if q['QDep'] != DEPTH:
                    continue
                cnt += 1
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
                    try:
                        asp_run_result = asp_run(prgm, asp_parse_conclusion([new_goal])[0], output_style=None)
                    except RecursionError:
                        print(json.dumps(q, indent=4))
                        pass
                    if asp_run_result["satisfactory"] != "Satisfied":
                        miss_cnt += 1
                        continue
                        # print(json.dumps(q, indent=4))
                        # print(json.dumps(prgm, indent=4))
                        # print(json.dumps(asp_run_result, indent=4))
                        # exit(0)
                results.append({
                    "id": idx,
                    "body_text": data['theory'],
                    "rule_names": [],
                    "goal": goal,
                    "label": q["answer"], # == False
                    "program": prgm
                })
    print(cnt, miss_cnt)
    # Sample only 300 examples
    shuffle(results)
    results = results[:300]
    with open(f"data/ruletaker_depth{DEPTH}/test_data.json", "w") as file:
        json.dump(results, file, indent=4)