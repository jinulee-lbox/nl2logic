from nl2logic.database_utils.queries import *

def viewConstName():
    const = input("찾고 싶은 상수명: ")
    # asp_term 검색
    print("Terms")
    cnt = 0
    for elem in db.query(f"SELECT id, term FROM asp_term WHERE term LIKE \"%{const}%\""):
        print(f"({elem['id']}) {elem['term']}")
        cnt += 1
    print("Total ", cnt, " results\n")
    
    # asp_conclusion 검색
    print("Conclusions")
    cnt = 0
    for elem in db.query("SELECT id, conclusion FROM asp_conclusion WHERE conclusion LIKE \"%{const}%\""):
        print(f"({elem['id']}) {elem['conclusion']}")
        cnt += 1
    print("Total ", cnt, " results\n")

    # data_case 검색
    print("Case")
    cnt = 0
    for elem in db.query("SELECT id, case_id, asp_code FROM data_case"):
        if const in elem['asp_code']:
            print(f"({elem['id']}) {elem['case_id']}")
            cnt += 1
    print("Total ", cnt, " results\n")

    # data_law 검색
    print("Law")
    cnt = 0
    for elem in db.query("SELECT id, law_id asp_code FROM data_law"):
        if const in elem['asp_code']:
            print(f"({elem['id']}) {elem['law_id']}")
            cnt += 1
    print("Total ", cnt, " results\n")

def changeConstName():
    original_const = input("바꾸고 싶은 상수명: ")
    new_const = input("새로운 상수명     : ")
    
    const_id = db.query("SELECT id, const FROM asp_const WHERE const = %s", (original_const,))[0]['id']
    # asp_const 교체
    db.query("UPDATE asp_const SET const=%s WHERE id=%s", (new_const, const_id))

    # asp_term 교체
    for elem in db.query(f"SELECT id, term FROM asp_term WHERE term LIKE \"%{original_const}%\""):
        id = elem['id']
        new_text = elem['term'].replace(original_const, new_const)
        db.query("UPDATE asp_term SET term=%s WHERE id=%s", (new_text, id))
    
    # asp_conclusion 교체
    for elem in db.query("SELECT id, conclusion FROM asp_conclusion WHERE conclusion LIKE \"%{original_const}%\""):
        id = elem['id']
        new_text = elem['conclusion'].replace(original_const, new_const)
        db.query("UPDATE asp_conclusion SET conclusion=%s WHERE id=%s", (new_text, id))

    # data_case 교체
    for elem in db.query("SELECT id, asp_code FROM data_case"):
        id = elem['id']
        new_text = elem['asp_code'].replace(original_const, new_const)
        db.query("UPDATE data_case SET asp_code=%s WHERE id=%s", (new_text, id))

    # data_law 교체
    for elem in db.query("SELECT id, asp_code FROM data_law"):
        id = elem['id']
        new_text = elem['asp_code'].replace(original_const, new_const)
        db.query("UPDATE data_law SET asp_code=%s WHERE id=%s", (new_text, id))


def changeConstNameToSuperConcept():
    original_const = input("바꾸고 싶은 상수명 : ")
    new_const =      input("새로운 superconcept: ")
    predicate =      input("predicate          : ")
    assert new_const.startswith(predicate)
    
    print(original_const)
    const_id = db.query("SELECT id, const FROM asp_const WHERE const = %s", (original_const,))[0]['id']
    pred_id = db.query("SELECT id, const FROM asp_const WHERE const = %s", (predicate,))[0]['id']

    # asp_term 교체
    for elem in db.query(f"SELECT id, term FROM asp_term WHERE term LIKE \'%{original_const}%\'"):
        id = elem['id']
        new_text = elem['term'].replace(original_const, new_const)
        db.query("UPDATE asp_term SET term=%s WHERE id=%s", (new_text, id))
    
    # asp_conclusion 교체
    for elem in db.query("SELECT id, conclusion FROM asp_conclusion WHERE conclusion LIKE \'%{original_const}%\'"):
        id = elem['id']
        new_text = elem['conclusion'].replace(original_const, new_const)
        db.query("UPDATE asp_conclusion SET conclusion=%s WHERE id=%s", (new_text, id))

    # data_case 교체
    for elem in db.query("SELECT id, asp_code FROM data_case"):
        id = elem['id']
        new_text = elem['asp_code'].replace(original_const, new_const)
        db.query("UPDATE data_case SET asp_code=%s WHERE id=%s", (new_text, id))

    # data_law 교체
    for elem in db.query("SELECT id, asp_code FROM data_law"):
        id = elem['id']
        new_text = elem['asp_code'].replace(original_const, new_const)
        db.query("UPDATE data_law SET asp_code=%s WHERE id=%s", (new_text, id))

    # 새로운 constant로 추출
    # rel_*_const 테이블 교체
    db.query("UPDATE rel_term_const SET const_id = %s WHERE const_id = %s", (pred_id, const_id))
        
    # asp_const 삭제
    db.query("DELETE FROM asp_const WHERE id=%s", (const_id,))

if __name__ == "__main__":
    db = DatabaseAPI("nl2logic")

    print("온톨로지 편집 CLI")
    print("\n=================================")
    print("1. 단어의 모든 등장 출처 찾아주기")
    print("2. 이름만 바꾸기")
    print("3. 논항 0 -> 상위 카테고리 + 스트링으로 교체\n")

    mode = int(input("모드: "))
    if mode not in [1,2,3]:
        print("잘못된 모드입니다. 프로그램을 종료합니다.")
        exit()
    print()
    while True:
        if mode == 1:
            viewConstName()

        if mode == 2:
            changeConstName()
        
        if mode == 3:
            changeConstNameToSuperConcept()