from typing import *
import requests
import re

from .logic_utils import asp_reformat_str

def lbox_case_exists(case_id):
    url = "https://lbox.kr/api/case"
    payload = {'id': case_id}
    response = requests.get(url, params=payload)

    return response.status_code == 200

def parse_form_to_asp(data, id=None, case=True, skip_if_fail=False):
    # Generate full ASP code
    if case:
        full_asp =  f"%% case_id\n"
    else:
        full_asp =  f"%% law_id\n"
    full_asp += f"% {id}\n\n"

    full_asp += f"%% terms\n"
    for term in data['terms']:
        # remove whitespace for retrieval simplicity
        term['asp'] = asp_reformat_str(term['asp'], skip_if_fail=skip_if_fail)
        # add body code
        full_asp += f"{term['asp']} % {term['comment']} % {term['source']}\n"
    full_asp += "\n"

    if case:
        full_asp += f"%% conclusion\n"
        for conc in data['concs']:
            # remove whitespace for retrieval simplicity
            conc['asp'] = asp_reformat_str(conc['asp'], skip_if_fail=skip_if_fail)
            # add body code
            full_asp += f"% {conc['asp']} % {conc['comment']} % {conc['source']}\n"
    # Full ASP code is generated
    return full_asp

def parse_case_asp_to_form(asp_code: str):
    # FSM-based line-by-line parser
    states = [
        "case_id_title",
        "case_id",
        "terms_title",
        "terms",
        "concs",
        "eof"
    ]
    state = "case_id_title"

    result = {}
    terms = None
    concs = None
    for line in asp_code.split("\n"):
        assert state in states
        if line == "":
            continue # empty line

        elif state == "case_id_title" and line.startswith(r"%%"):
            state = "case_id"

        elif state == "case_id" and line.startswith(r"%"):
            # Parse case_id into courtname and casenum
            case_id = line.replace("%", "").replace(" ", "")
            assert lbox_case_exists(case_id)
            courtname = re.search("^[가-힣]+", case_id).group(0)
            assert courtname
            casenum = case_id.replace(courtname + "-", "")
            assert casenum
            result["courtname"] = courtname
            result["casenum"] = casenum
            state = "terms_title"

        elif state == "terms_title" and line.startswith(r"%%"):
            terms = []
            state = "terms"
        elif state == "terms" and not line.startswith("%"):
            term = line.split(" % ")
            assert len(term) == 3
            terms.append({
                "asp": term[0].strip(),
                "comment": term[1].strip(),
                "source": term[2].strip()
            })
        elif state == "terms" and line.startswith(r"%%"):
            concs = []
            state = "concs"
        elif state == "concs" and line.startswith(r"%"):
            conc = line.split("% ")[1:]
            assert len(conc) == 3
            concs.append({
                "asp": conc[0].strip(),
                "comment": conc[1].strip(),
                "source": conc[2].strip()
            })
        else:
            raise ValueError(f"Invalid ASP code, parsing `{state}`")
    
    result['terms'] = terms
    result['concs'] = concs
    return result

def parse_law_asp_to_form(asp_code: str):
    # FSM-based line-by-line parser
    states = [
        "law_id_title",
        "law_id",
        "terms_title",
        "terms",
        "eof"
    ]
    state = "law_id_title"

    result = {}
    terms = None
    for line in asp_code.split("\n"):
        assert state in states
        if line == "":
            continue # empty line

        elif state == "law_id_title" and line.startswith(r"%%"):
            state = "law_id"

        elif state == "law_id" and line.startswith(r"%"):
            # Parse law_id
            law_id = line.replace("%", "").replace(" ", "")
            result["lawname"] = law_id
            state = "terms_title"

        elif state == "terms_title" and line.startswith(r"%%"):
            terms = []
            state = "terms"
        elif state == "terms" and not line.startswith("%"):
            term = line.split(" % ")
            assert len(term) == 3
            terms.append({
                "asp": term[0].strip(),
                "comment": term[1].strip(),
                "source": term[2].strip()
            })
        else:
            raise ValueError(f"Invalid ASP code, parsing `{state}`")
    
    result['terms'] = terms
    return result
