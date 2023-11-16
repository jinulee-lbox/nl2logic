
from .logic_utils import *
from .database_utils import *
from .utils import *

def validity_check(data, mode):
    assert mode in ['case', 'law']

    program = [{
        'asp': asp_reformat_str(term['asp'], skip_if_fail=True),
        'comment': term['comment']
    } for term in data['terms']]
    if mode == 'case':
        conclusions = [asp_reformat_str(conc['asp'], skip_if_fail=True) for conc in data['concs']]

    validity_flag = True
    validity_msg = []

    # 1) 법원/사건번호 syntax/validity check
    case_id_success = 0
    if mode == 'case':
        case_id = data['courtname'] + '-' + data['casenum']
        case_id_success = 0
        if not lbox_case_exists(case_id):
            case_id_success = 1
            validity_flag = False
            validity_msg.append("잘못된 사건명입니다. (법원명, 사건번호)")
    elif mode == "law":
        law_id = data['lawname']

    # 2) Check if asp/comments are not empty/duplicate
    if len(program) == 0:
        validity_msg.append("ASP 코드가 비어 있습니다.")
        validity_flag = False
    if mode == 'case':
        if len(conclusions) == 0:
            validity_msg.append("증명하려는 결론이 비어 있습니다.")
            validity_flag = False

    asp_exist_empty = False
    asp_exist_duplicate = False
    asp_duplicate_set = set(); asp_duplicate_list = []
    nl_exist_empty = False
    nl_exist_duplicate = False
    nl_duplicate_set = set(); nl_duplicate_list = []
    for term in data['terms']:
        if mode=="case" and not term['fromPrecedent']:
            continue
        if term['asp'].strip() == "":
            asp_exist_empty = True
        elif term['asp'].strip() in asp_duplicate_set:
            asp_exist_duplicate = True
            asp_duplicate_list.append(term['asp'].strip())
        asp_duplicate_set.add(term['asp'].strip())

        if term['comment'].strip() == "":
            nl_exist_empty = True
        elif term['comment'].strip() in nl_duplicate_set:
            nl_exist_duplicate = True
            nl_duplicate_list.append(term['comment'].strip())
        nl_duplicate_set.add(term['comment'].strip())
    
    if asp_exist_empty:
        validity_msg.append("빈 ASP 코드가 존재합니다.")
        validity_flag = False
    if asp_exist_duplicate:
        validity_msg.append("중복된 ASP 코드가 존재합니다. " + ",".join(asp_duplicate_list))
        validity_flag = False
    if nl_exist_empty:
        validity_msg.append("빈 자연어 설명이 존재합니다.")
        validity_flag = False
    if nl_exist_duplicate:
        validity_msg.append("중복된 자연어 설명이 존재합니다. " + ",".join(nl_duplicate_list))
        validity_flag = False
    
    # 3) Terms parsing
    preprocessed_program, prgm_success = asp_parse_program(program)
    conc_symbols = []
    conc_success = []
    for result in prgm_success:
        if result['code'] != 0:
            validity_flag = False
            validity_msg.append("ASP 프로그램 본문 에러")
            break
    if mode == "case":
        conc_symbols, conc_success = asp_parse_conclusion(conclusions)
        for result in conc_success:
            if result['code'] != 0:
                validity_flag = False
                validity_msg.append("ASP 결론 에러")
                break

    # 4) Check if all symbols are available from the ontology
    missing_ontology_total = []
    for pgm, success in zip(program, prgm_success):
        try:
            const_list = asp_extract_const_list(pgm["asp"], exclude_underscore=True)
            missing_ontology = db_find_missing_ontology(const_list)
            if len(missing_ontology) > 0 and success['code'] == 0:
                success['code'] = 11 # missing ontology
                success['msg'] = "Missing ontology: [" + ', '.join(missing_ontology) + "]"
            missing_ontology_total.extend(missing_ontology)
        except Exception as e:
            pass
    
    missing_ontology_total = sorted(list(set(missing_ontology_total)))
    if len(missing_ontology_total) > 0:
        validity_flag = False
        validity_msg.append(f"온톨로지 DB에 등록되지 않은 단어: [{', '.join(missing_ontology_total)}]")

    # 5) Run ASP
    asp_result = asp_run(program, conc_symbols)
    # check validity
    if mode == "case":
        all_conc_proved = True
        unproved_conc = []
        for conc in asp_result['proofs']:
            if conc['proved'] == 0:
                all_conc_proved = False
                unproved_conc.append(conc['conclusion'])
        if not all_conc_proved:
            validity_flag = False
            validity_msg.append(f"원하는 결론이 증명되지 않았음: {str(unproved_conc)}")
    
    response_data = {
        "case_id_parse_success": case_id_success,   # 1) validity information for 법원/사건번호
        "program_parse_success": prgm_success,      # 2) success(0) / syntax(10) / ontology(11) error
        "conclusion_parse_success": conc_success,   # 2) success(0) / syntax(10) / ontology(11) error
        "asp_result": asp_result,                # 3) SAT / proof result for each answer set(model)
        "validity": 0 if validity_flag else 1, # 0: valid, 1: invalid
        "validity_message": validity_msg,
        "database_message": None
    }
    return response_data