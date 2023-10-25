import json
from chain.convert_doc_to_asp import convert_doc_to_asp
from nl2logic.config import set_logger
from nl2logic.graphviz_utils import justification_tree_to_graphviz, graphviz_to_png

if __name__ == "__main__":
    set_logger("langchain")

    # document = """ 피고인 A.
    # 피고인은 포터Ⅱ 화물차의 운전업무에 종사하는 사람으로, 자동차운전면허를 받지 아니하고 부산 연제구 D에 있는 E 앞 편도 3차로 도로를 연산교차로 방면에서 신리교차로 방면으로 진행하고 있었다.
    # 이러한 경우 운전업무에 종사하는 사람에게는 조향 및 제동장치를 정확히 조작하여 사고를 방지할 업무상 주의의무가 있었다.
    # 그럼에도 피고인은 이를 게을리 한 채 그대로 진행한 과실로 피고인의 진행방향 앞에서 차량 정지신호에 따라 정차하던 피해자 F(여, 40세)가 운전하는 (차량번호 2 생략) SM6 승용차의 뒷범퍼 부분을 위 화물차 앞범퍼 부분으로 들이받았다.
    # 결국 피고인은 위와 같은 업무상 과실로 피해자 F에게 약 2주간의 치료가 필요한 ‘경추의 염좌 및 긴장’ 등의 상해를 입게 하였다.
    # 피고인은 자동차종합보험에 가입되어 있다.
    # """
    document = """
    피고인 A는 포터Ⅱ 화물차를 몰고 B에 위치한 C 도로를 D 방면에서 E 방면으로 진행하였다.
    이러한 경우 운전업무에 종사하는 사람에게는 조향장치를 정확히 조작할 업무상 주의의무가 있었다.
    그럼에도 피고인은 이를 게을리 한 채 그대로 진행하였다.
    피고인은 피해자 F가 운전하는 SM6 승용차를 위 화물차로 들이받았다.
    피고인은 피해자 F에게 약 3주간의 치료가 필요한 경추의 염좌 등의 상해를 입게 하였다.
    피고인은 자동차종합보험에 가입되어 있다.
    피고인 A는 자동차운전면허를 보유하지 않았다.
    """
    result, program = convert_doc_to_asp({
        "body_text": document,
        "law_id": "교통사고처리특례법위반(치상)",
        "verdict": "guilty"
    }, few_shot_n=8)
    result = result[0] # First goal only

    # graph = justification_tree_to_graphviz(result)
    # graphviz_to_png(graph, "test/treetest.svg")

    print(str(result))
    # print(convert_proof_tree_to_nl(result))