import json
import re
from nl2logic.database_utils import db_get_asp_body_from_law_id
from pysolver.utils import parse_line

def get_skip_words(law_id, body_text):
    skip_words = []
    # Heuristic for removing irrelelvant words.
    if law_id == "형사일반":
        if "방위" not in body_text:
            skip_words.append("정당방위")
        if "피난" not in body_text:
            skip_words.append("긴급피난")
        if "정당행위" not in body_text:
            skip_words.append("정당행위")
        if "승낙" not in body_text:
            skip_words.append("승낙")
        if "자구" not in body_text:
            skip_words.append("자구행위")
        skip_words.append("-responsible(D) :- ")

    if law_id == "교통사고처리특례법위반(치상)":
        if "신호" not in body_text:
            skip_words.append("신호위반")
        if "중앙선" not in body_text:
            skip_words.append("중앙선")
        if "과속" not in body_text:
            skip_words.append("과속")
        if "앞지르기" not in body_text and "끼어들기" not in body_text:
            skip_words.append("앞지르기방법위반")
        if "건널목" not in body_text:
            skip_words.append("건널목")
        if "횡단보도" not in body_text:
            skip_words.append("횡단보도보행자보호의무위반")
        if "면허" not in body_text:
            skip_words.append("무면허운전")
        if "음주" not in body_text and "알코올" not in body_text and "약물" not in body_text:
            skip_words.append("음주운전")
        if "보도" not in body_text:
            skip_words.append("보도침범")
        if "승객" not in body_text:
            skip_words.append("승객추락방지의무위반")
        if "어린이" not in body_text:
            skip_words.append("어린이보호구역내안전운전의무위반")
        if "고정" not in body_text and "조치" not in body_text:
            skip_words.append("화물고정조치위반")

    return skip_words

def get_initial_program(doc):
    law_ids = []
    law_ids.append(doc['law_id'])
    # Add default keys
    if "형사일반" not in law_ids:
        law_ids.append("형사일반")

    program = []
    visited = set() # memoization
    while len(law_ids) > 0:
        law_id = law_ids.pop()
        visited.add(law_id)
        new_program = json.loads(db_get_asp_body_from_law_id(law_id))["terms"]
        # Reduce size of program
        SKIP_WORDS = get_skip_words(law_id, doc["body_text"])
        def skip(asp_str):
            for skip_word in SKIP_WORDS:
                if skip_word in asp_str:
                    return True
            return False
        new_program = [x for x in new_program if not skip(x["asp"])]
        program += new_program

        # Check if recursive inclusion is required
        raw_str_program = "\n".join([x["asp"] for x in new_program])
        for new_law_id in re.findall(r"crime\(\"([ㄱ-ㅣ가-힣() ]+)\"\)", raw_str_program):
            if new_law_id not in visited:
                law_ids.append(new_law_id)
    return program

def get_goals(doc):
    results = []
    results.append(
        parse_line(f"{doc['verdict']}(defendant(\"A\"), crime(\"{doc['law_id']}\"),_).").head
    )
    return results