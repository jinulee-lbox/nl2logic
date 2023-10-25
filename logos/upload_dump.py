import json
import re
from tqdm import tqdm

from nl2logic.database_utils.db_utils import DatabaseAPI

file_dir = "data/precedent_traffic_crimes.jsonl"
target_casename = set([
    "특정범죄가중처벌등에관한법률위반(도주치상)",
    "도로교통법위반(음주측정거부)",
    "도로교통법위반(사고후미조치)",
    "도로교통법위반(음주운전)",
    "특정범죄가중처벌등에관한법률위반(위험운전치상)",
    "교통사고처리특례법위반(치상)",
    "도로교통법위반(무면허운전)",
    # "도로교통법위반" # 업무상과실 재물손괴??
])

def main():
    with open(file_dir, "r", encoding="UTF-8") as f:
        # Final result
        cnt = 0
        result = []
        for line in f:
            cnt += 1
            data = json.loads(line)

            try: # Key check
                # Section list
                order_of_judgement = [x for x in data["section_list"] if x["title"] == "주문"][0]["text"].split("\n")
                defendant = [x for x in data["section_list"] if x["title"] == "피고인"][0]
                reason = [x for x in data["section_list"] if "이유" in x["title"]][0]["text"].split("\n")
                data["casename_list"]
                data["facts"]
                len(data["facts"]["casenames"])
            except Exception as e:
                # print(e)
                continue

            # Filter only first trial
            if not re.match(".*원-[0-9]+고.?[0-9]+", data["doc_id"]):
                continue
            # Filter by casename (remove irrelevant cases)
            verdict_map = {} # casename and verdict pairs
            only_given_casename = True
            for casename in data["casename_list"]:
                if casename not in target_casename:
                    only_given_casename = False
                    break
            if not only_given_casename:
                continue
            # Initialize casename-verdict map
            for casename in data["casename_list"]:
                verdict_map[casename] = "guilty"
            # Filter by defendant name
            if defendant["text"] != "A":
                continue

            # Extract verdict(guilty, dismissal charge or innocent)
            extract_verdict_success = True
            exist_innocent = False
            for order in order_of_judgement:
                try:
                    if "무죄" in order and "공시" not in order:
                        exist_innocent = True
                        # print(order)
                        parsed_casename = re.findall("(^|\s)([^\s]*)(의 점|죄|은|는)", order)
                        for _, casename, _ in parsed_casename:
                            # print("무죄 죄명:", casename, casename in verdict_map)
                            if casename in verdict_map:
                                verdict_map[casename] = "innocent"
                    elif "공소" in order and "기각" in order:
                        exist_innocent = True
                        # print(order)
                        parsed_casename = re.findall("(^|\s)([^\s]*)(의 점|죄|은|는)", order)
                        for _, casename, _ in parsed_casename:
                            # print("공소기각 죄명:", casename, casename in verdict_map)
                            if casename in verdict_map:
                                verdict_map[casename] = "dismissalOfIndictment"
                    else:
                        continue
                except Exception as e:
                    print(order)
                    print(e)
                    extract_verdict_success = False
                    # exit()
            if not extract_verdict_success:
                continue
            # if exist_innocent:
            #     print("")
            #     print(verdict_map)

            # Extract fact sentences
            fact_map = {}
            all_fact_sent_indices = set([-1])
            for fact in data["facts"]["casenames"]:
                casenames = fact["casename"]
                # Parse casename
                casenames = re.sub(r"^[0-9]+\.\s*", "", casenames) # remove `1. ` like header
                casenames = casenames.split(", ") # Split casenames
                for c in casenames:
                    c = c.strip() 
                    fact_map[c] = fact
                all_fact_sent_indices.update(fact["sent_indexes"])

            # Add casenames
            for casename in data["casename_list"]:
                # if exist_innocent:
                #     print("-", casename, verdict_map[casename] if casename in verdict_map else "")
                
                # Aggregate relevant facts
                body_text = ""

                # `fact` field contains casename
                if casename in fact_map:
                    fact = fact_map[casename]
                    sent_indices = fact["sent_indexes"]
                    sent_indices = [x-1 for x in sent_indices] # this field starts from 1
                    sents = [reason[i] for i in sent_indices]
                    if verdict_map[casename] == "guilty":
                        body_text += "범죄사실\n" + "\n".join(sents)
                    # else:
                    #     body_text += "공소사실\n" + "\n".join(sents)
                
                # court's decision about the prosecutor opinion (공소사실에 대한 판단)
                if verdict_map[casename] == "innocent":
                    body_text = ""
                    innocent_reason_zone = 0
                    for i in range(len(reason)):
                        # Finite state control for parsing
                        if re.search(r"무\s*죄", reason[i]) and innocent_reason_zone == 0:
                            innocent_reason_zone = 1
                        if re.search(r"결\s*론", reason[i]):
                            innocent_reason_zone = 2
                        
                        # If valid reason, add to body_text
                        if innocent_reason_zone == 1 and i > max(all_fact_sent_indices): # 개별 사건 사실관계 나온 후 무죄/공소기각 나온다고 가정
                            body_text += reason[i] + "\n"
                    body_text = body_text.rstrip("\n")
                if verdict_map[casename] == "dismissalOfIndictment":
                    body_text = ""
                    innocent_reason_zone = 0
                    for i in range(len(reason)):
                        # Finite state control for parsing
                        if re.search(r"공\s*소\s*기\s*각", reason[i]) and innocent_reason_zone == 0:
                            innocent_reason_zone = 1
                        if re.search(r"결\s*론", reason[i]):
                            innocent_reason_zone = 2
                        
                        # If valid reason, add to body_text
                        if innocent_reason_zone == 1 and i > max(all_fact_sent_indices): # 개별 사건 사실관계 나온 후 무죄/공소기각 나온다고 가정
                            body_text += reason[i] + "\n"
                    body_text = body_text.rstrip("\n")
                
                # If no relevant text is found,
                if body_text == "":
                    continue
            
                result.append({
                    "case_id": data["doc_id"],
                    "body_text": body_text,
                    "law_id": casename,
                    "verdict": verdict_map[casename]
                })

    # Complete
    print(cnt, len(result))
    # Statistics
    verdict_count = {"guilty": 0, "innocent": 0, "dismissalOfIndictment": 0}
    casename_count = {x:0 for x in target_casename}
    for r in result:
        verdict_count[r["verdict"]] += 1
        casename_count[r["law_id"]] += 1
    print(verdict_count)
    print(casename_count)

    # Upload to DB
    print("Upload DB")
    db = DatabaseAPI("nl2logic")
    db.query("TRUNCATE table data_rawcase")
    for x in tqdm(result):
        db.query(
            "INSERT INTO data_rawcase (case_id, body_text, law_id, verdict) VALUES (%s,%s,%s,%s)",
            (x["case_id"], x["body_text"], x["law_id"], x["verdict"])
        )
    db.close()

if __name__ == "__main__":
    main()