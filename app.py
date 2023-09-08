"""
Flask application to control submission.
"""
from flask import Flask, request, jsonify
import json
import logging

from nl2logic.validity import validity_check
from nl2logic.asp_utils import *
from nl2logic.database_utils import *
from nl2logic.config import nl2logic_config as config
from nl2logic.config import set_logger

app = Flask(__name__, static_url_path='')

@app.route('/test_asp', methods=['POST'])
def test_asp():
    """
    Handle Test ASP submission
    1. validity check & run asp
    2. Return response to client
    """
    data = request.get_json()
    case_id = data['courtname'] + '-' + data['casenum']

    response_data = validity_check(data, mode="case")

    ##### Return response #####
    response_data['database_message'] = ["DB에 업데이트하려면 'DB에 등록하기' 버튼을 사용해주세요."]
    return jsonify(response_data), 200

@app.route('/update_case_db', methods=['POST'])
def update_case_db():
    """
    Handle `data_case` update.
    1. validity check & run asp
    2. Update terms DB
    3. Return response to client
    """
    data = request.get_json()
    case_id = data['courtname'] + '-' + data['casenum']

    response_data = validity_check(data, mode="case")

    ##### Update terms DB #####
    # Only update DB if validity check has been passed!!!!
    db_msg = []
    if response_data["validity"] == 0:
        try:
            db_delete_case(case_id) # delete current case and remove consequences
            db_msg.append(f"기존 {case_id} 데이터 삭제 성공")
            try:
                db_insert_case(data) # insert case, terms, conclusions, and required relations
                db_msg.append(f"{case_id} 데이터 업데이트 성공")
            except Exception as e:
                db_msg.append(f"{case_id} 추가 실패: {e.__class__} {str(e)}")
                db_delete_case(case_id)
                db_msg.append(f"추가 실패 -> {case_id} 잔여 데이터 삭제 성공")
        except Exception as e:
            db_msg.append(f"기존 판례({case_id}) 삭제 실패: {e.__class__} {str(e)}")
        # DEBUG
        # db_delete_case(case_id) # delete current case and remove consequences
        # db_insert_case(data) # insert case, terms, conclusions, and required relations

    ##### Return response #####
    response_data['database_message'] = db_msg
    
    # 3) ASP run results
    return jsonify(response_data), 200


@app.route('/tempsave_case_db', methods=['POST'])
def tempsave_case_db():
    """
    Handle Test ASP submission
    1. validity check & run asp
    2. Update terms DB
    3. Return response to client
    """
    data = request.get_json()
    case_id = data['courtname'] + '-' + data['casenum']

    ##### Update temp DB #####
    db_msg = []
    try:
        db_insert_case_temp(data) # insert case, terms, conclusions, and required relations
        db_msg.append(f"{case_id} 임시저장 성공")
    except Exception as e:
        db_msg.append(f"({case_id}) 임시저장 실패: {e.__class__} {str(e)}")

    ##### Return response #####
    response_data = {
        "database_message": db_msg
    }
    response_data['database_message'] = db_msg
    
    # 3) ASP run results
    return jsonify(response_data), 200

@app.route('/update_law_db', methods=['POST'])
def update_law_db():
    """
    Handle Law DB submission
    1. validity check
    2. Update terms DB
    3. Return response to client
    """
    data = request.get_json()
    law_id = data['lawname']

    response_data = validity_check(data, mode="law")

    ##### Update terms DB #####
    # Only update DB if validity check has been passed!!!!
    db_msg = []
    if response_data["validity"] == 0:
        try:
            case_for_law = db_delete_law(law_id) # delete current law and remove consequences
            db_msg.append(f"기존 {law_id} 데이터 삭제 성공")
            try:
                db_insert_law(data, case_for_law) # insert law, terms, conclusions, and required relations
                db_msg.append(f"{law_id} 데이터 업데이트 성공")
            except Exception as e:
                db_msg.append(f"{law_id} 추가 실패: {e.__class__} {str(e)}")
                db_delete_law(law_id)
                db_msg.append(f"추가 실패 -> {law_id} 잔여 데이터 삭제 성공")
        except Exception as e:
            db_msg.append(f"기존 판례({law_id}) 삭제 실패: {e.__class__} {str(e)}")
        # DEBUG
        # case_for_law = db_delete_law(law_id)
        # db_insert_law(data, case_for_law)

    ##### Return response #####
    response_data['database_message'] = db_msg
    
    # 3) ASP run results
    return jsonify(response_data), 200



@app.route('/get_case_form', methods=['GET'])
def get_case_form():
    case_id = request.args.get('case_id')

    try:
        result, is_temp = db_get_asp_body_from_case_id(case_id)
        result = json.loads(result)
        if is_temp:
            result['laws'] = db_get_law_from_case(case_id, temp=True)
        else:
            result['laws'] = db_get_law_from_case(case_id)
        return jsonify(result), 200
    except ValueError as e:
        logging.error(str(e))
        return jsonify({}), 200

@app.route('/get_law_form', methods=['GET'])
def get_law_form():
    law_id = request.args.get('law_id')

    try:
        result = db_get_asp_body_from_law_id(law_id)
        result = json.loads(result)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({}), 200
    
if __name__ == '__main__':
    set_logger("webserver")
    app.run(host='0.0.0.0', port=config.webserver.port)