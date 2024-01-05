import json
import random
import logging

from nl2logic.database_utils.db_utils import DatabaseAPI
from polar.chain.components.initialize_asp_from_json import get_initial_program, get_goals

from polar.chain.utils import config, PolarContext

file_dir = "data/precedent_traffic_crimes.jsonl"
target_casename = [
    "특정범죄가중처벌등에관한법률위반(도주치상)",
    "도로교통법위반(음주측정거부)",
    "도로교통법위반(사고후미조치)",
    "도로교통법위반(음주운전)",
    "특정범죄가중처벌등에관한법률위반(위험운전치상)",
    "교통사고처리특례법위반(치상)",
    "도로교통법위반(무면허운전)",
    # "도로교통법위반" # 업무상과실 재물손괴??
]

NUM_PER_GUILTY_CASE = 20
NUM_PER_INNOCENT_CASE = 10

def main():
    random.seed(41)
    db = DatabaseAPI("nl2logic")
    case_data = []
    idx = 0
    # dataset = PolarContext(config, dataset)
    for casename in target_casename:
        # Select guilty
        rawcase = db.query("SELECT * FROM data_rawcase WHERE law_id = %s AND verdict = %s", (casename, "guilty"))
        random.shuffle(rawcase)
        cases = rawcase[:NUM_PER_GUILTY_CASE]
        for case in cases:
            goal = get_goals(case)[0]
            case["goal"] = goal; case["label"] = True
            rules = get_initial_program(case, None)
            for rule in rules:
                rule["statement"] = rule.pop("asp")
                rule["description"] = rule.pop("comment")
            case["world_model"] = rules
            case["program"] = []
            case.pop("verdict")
            case.pop("case_id")
            case.pop("law_id")
        case_data.extend(cases)
    for casename in target_casename:
        # Select guilty
        rawcase = db.query("SELECT * FROM data_rawcase WHERE law_id = %s AND verdict = %s", (casename, "innocent"))
        random.shuffle(rawcase)
        cases = rawcase[:NUM_PER_INNOCENT_CASE]
        for case in cases:
            goal = get_goals(case)[0]
            case["goal"] = goal; case["label"] = True
            rules = get_initial_program(case, None)
            for rule in rules:
                rule["statement"] = rule.pop("asp")
                rule["description"] = rule.pop("comment")
            case["world_model"] = rules
            case["program"] = []
            case.pop("verdict")
            case.pop("case_id")
            case.pop("law_id")
        case_data.extend(cases)
    db.close()
    print(json.dumps(case_data[0], indent=4, ensure_ascii=False))
    # print(json.dumps(get_initial_program(case_data[0], None), indent=4, ensure_ascii=False))
    with open("data/sstar/test_data_raw.json", "w") as file:
        json.dump(case_data, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()