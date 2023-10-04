import json
import re
from nl2logic.database_utils.queries import db_get_asp_body_from_law_id

def get_initial_program(doc):
    law_ids = []
    for conc in doc['conclusion']:
        law_ids.append(conc['law_id'])
    # Add default keys
    if "형사일반" not in law_ids:
        law_ids.append("형사일반")

    program = []
    visited = set() # memoization
    while len(law_ids) > 0:
        law_id = law_ids.pop()
        visited.add(law_id)
        new_program = json.loads(db_get_asp_body_from_law_id(law_id))["terms"]
        program += new_program

        # Check if recursive inclusion is required
        raw_str_program = "\n".join([x["asp"] for x in new_program])
        for new_law_id in re.findall(r"crime\(\"([ㄱ-ㅣ가-힣() ]+)\"\)", raw_str_program):
            if new_law_id not in visited:
                law_ids.append(new_law_id)
    return program

def get_goals(doc):
    results = []
    for conc in doc['conclusion']:
        results.append(f"{conc['verdict']}(defendant(\"A\"), crime(\"{conc['law_id']}\")).")
    return results