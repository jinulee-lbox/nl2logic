import json
import random
import logging

from nl2logic.database_utils.db_utils import DatabaseAPI
from nl2logic.config import set_logger
from chain.convert_doc_to_asp import convert_doc_to_asp

file_dir = "data/precedent_traffic_crimes.jsonl"
target_casename = [
    "특정범죄가중처벌등에관한법률위반(도주치상)",
    # "도로교통법위반(음주측정거부)",
    # "도로교통법위반(사고후미조치)",
    # "도로교통법위반(음주운전)",
    # "특정범죄가중처벌등에관한법률위반(위험운전치상)",
    # "교통사고처리특례법위반(치상)",
    # "도로교통법위반(무면허운전)",
    # "도로교통법위반" # 업무상과실 재물손괴??
]

NUM_PER_CASE = 20

def main():
    set_logger("langchain")

    random.seed(41)
    db = DatabaseAPI("nl2logic")
    case_data = []
    for casename in target_casename:
        # Select guilty
        rawcase = db.query("SELECT * FROM data_rawcase WHERE law_id = %s AND verdict = %s", (casename, "guilty"))
        random.shuffle(rawcase)
        case_data.extend(rawcase[:NUM_PER_CASE])
    db.close()

    for case in case_data[3:4]:
        print(json.dumps(case, indent=4, ensure_ascii=False))
        result, program = convert_doc_to_asp(case, few_shot_n=8)
        result = result[0] # First goal only
        # with open("logs/logos_trial_result.txt", "a") as file:
        #     file.write("==============================\n")
        #     file.write(f"{json.dumps(case, indent=4, ensure_ascii=False)}\n\n")
        #     file.write(str(result) + "\n")
        #     file.write(json.dumps(program, indent=4, ensure_ascii=False) + "\n\n")
        logging.info("==============================\n")
        logging.info(f"{json.dumps(case, indent=4, ensure_ascii=False)}\n\n")
        logging.info(str(result) + "\n")
        logging.info(json.dumps(program, indent=4, ensure_ascii=False) + "\n\n")

if __name__ == "__main__":
    main()