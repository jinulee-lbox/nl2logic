from .db_utils import DatabaseAPI
from ..logic_utils import asp_extract_const_list
import json
import random

def db_find_missing_ontology(const_list):
    db = DatabaseAPI('nl2logic')
    result = db.query("""
    SELECT * FROM asp_const
    """)
    current_ontology = [(d["const"], d["nargs"]) for d in result]

    missing_consts = [name+"/"+str(arity) for name, arity in const_list if ((name, arity) not in current_ontology)]
    db.close()
    return missing_consts

def db_delete_case(case_id):
    db = DatabaseAPI('nl2logic')

    # Check if case exists or not
    exists = len(db.query(f"""
    SELECT * FROM data_case WHERE case_id = %s
    """, (case_id,))) > 0
    if not exists:
        return

    # Delete case data with case_id
    db.query(f"""
    DELETE FROM data_case WHERE case_id = %s
    """, (case_id,))

    # by cascade, rel_case_* is auto-removed.
    # remove orphaned terms/conclusions.
    db.query(f"""
    DELETE FROM text_comment WHERE law_id IS NULL AND case_id NOT IN (SELECT id FROM data_case)
    """)
    db.query(f"""
    DELETE FROM asp_term
          WHERE asp_term.id NOT IN (SELECT term_id FROM rel_text_term)
    """)
    db.query(f"""
    DELETE FROM asp_conclusion
          WHERE asp_conclusion.id NOT IN (SELECT conclusion_id FROM rel_text_conclusion)
    """)
    db.close()

def db_insert_case(data):
    db = DatabaseAPI('nl2logic')

    # Case ID
    case_id_text = data['courtname'] + '-' + data['casenum']

    # truncate law ASP and only leave precedent-only
    data['terms'] = [d for d in data['terms'] if d['fromPrecedent']]

    # generate ASP from form data
    full_asp = json.dumps(data, ensure_ascii=False)

    # Add case data with case_id / ASP code
    db.query(f"""
    INSERT INTO data_case (case_id, asp_code) VALUES (%s, %s)
    """, (case_id_text, full_asp))
    case_id = db.query(f"""
        SELECT id, case_id FROM data_case WHERE case_id = '{case_id_text}'
    """)[0]['id']

    # Add term/conc data into DB
    term_ids = []
    for term in data['terms']:
        db.query("""
            INSERT IGNORE INTO asp_term (term) VALUES (%s)
        """, term['asp'])
        term_id = db.query(f"""
            SELECT * FROM asp_term WHERE term = %s
        """, (term['asp'],))[0]['id']
        assert term_id is not None
        term_ids.append(term_id)
    conc_ids = []
    for conc in data['concs']:
        db.query(f"""
            INSERT IGNORE INTO asp_conclusion (conclusion) VALUES (%s)
        """, (conc['asp'],))
        conc_id = db.query(f"""
            SELECT id, conclusion FROM asp_conclusion WHERE conclusion = %s
        """, conc['asp'])[0]['id']
        assert conc_id is not None
        conc_ids.append(conc_id)

    # Add comments data into DB
    nl_term_ids = []
    for term in data['terms']:
        db.query(f"""
            INSERT INTO text_comment (text, source, case_id) VALUES (%s, %s, %s)
        """, (term['comment'], term['source'],case_id))
        nl_term_id = db.query(f"""
            SELECT id, text, case_id FROM text_comment WHERE text = %s AND case_id = %s
        """, (term['comment'], case_id))[0]['id']
        nl_term_ids.append(nl_term_id)
    nl_conc_ids = []
    for conc in data['concs']:
        db.query(f"""
            INSERT INTO text_comment (text, source, case_id) VALUES (%s, %s, %s)
        """, (conc['comment'], conc['source'], case_id))
        nl_conc_id = db.query(f"""
            SELECT id, text, case_id FROM text_comment WHERE text = %s AND case_id = %s
        """, (conc['comment'], case_id))[0]['id']
        nl_conc_ids.append(nl_conc_id)
    
    # Add appropriate relations
    for text_id, term_id in zip(nl_term_ids, term_ids):
        db.query(f"""
        INSERT INTO rel_text_term (text_id, term_id) VALUES (%s, %s)
        """, (text_id, term_id))
    for text_id, conc_id in zip(nl_conc_ids, conc_ids):
        db.query(f"""
        INSERT INTO rel_text_conclusion (text_id, conclusion_id) VALUES (%s, %s)
        """, (text_id, conc_id))
    
    # Add case<->law relations
    law_ids = set()
    for law in data['laws']:
        law_ids.add(law['name'])
    for law_id in law_ids:
        # retrieve const ids
        law_id_num = db.query(f"""
        SELECT id, law_id FROM data_law WHERE law_id = %s
        """, (law_id,))[0]['id']
        # add relation
        db.query(f"""
        INSERT INTO rel_case_law (case_id, law_id) VALUES (%s, %s)
        """, (case_id, law_id_num))

    # Add term<->const relations
    for term, term_id in zip(data['terms'], term_ids):
        term_asp = term['asp']
        # extract constants
        const_list = list(set(asp_extract_const_list(term_asp)))
        const_list = [f"'{name}'" for name, arity in const_list]
        # retrieve const ids
        const_ids = db.query(f"""
        SELECT id, const FROM asp_const WHERE const IN ({', '.join(const_list)})
        """)
        const_ids = [x['id'] for x in const_ids]
        if len(const_list) != len(const_ids):
            raise ValueError("len(const_list) != len(const_ids)")
        # add relation
        for const_id in const_ids:
            db.query(f"""
            INSERT INTO rel_term_const (term_id, const_id) VALUES (%s, %s)
            """, (term_id, const_id))
    
    # Remove temporarily stored case
    db.query(f"""
    DELETE FROM data_case_temp WHERE case_id = %s
    """, (case_id_text,))
    db.close()

def db_insert_case_temp(data):
    db = DatabaseAPI('nl2logic')

    # Case ID
    case_id_text = data['courtname'] + '-' + data['casenum']
    db_delete_case(case_id_text)
    # truncate law ASP and only leave precedent-only
    data['terms'] = [d for d in data['terms'] if d['fromPrecedent']]

    # generate ASP from form data
    full_asp = json.dumps(data, ensure_ascii=False)

    # Add case data with case_id / ASP code
    db.query(f"""
    REPLACE INTO data_case_temp (case_id, asp_code) VALUES (%s, %s)
    """, (case_id_text, full_asp))
    case_id = db.query(f"""
        SELECT id, case_id FROM data_case_temp WHERE case_id = %s
    """, (case_id_text,))[0]['id']

    # Add case<->law relations
    law_ids = set()
    for law in data['laws']:
        law_ids.add(law['name'])
    for law_id in law_ids:
        # retrieve const ids
        law_id_num = db.query(f"""
        SELECT id, law_id FROM data_law WHERE law_id = %s
        """, (law_id,))[0]['id']
        # add relation
        db.query(f"""
        INSERT INTO rel_case_law_temp (case_id, law_id) VALUES (%s, %s)
        """, (case_id, law_id_num))

    db.close()

def db_get_asp_body_from_case_id(case_id) :
    db = DatabaseAPI('nl2logic')
    is_temp = False

    data = db.query(f"""
    SELECT * FROM data_case WHERE case_id = %s
    """, (case_id,))
    if len(data) == 0:
        # Attemp to load from temp DB.
        data = db.query(f"""
        SELECT * FROM data_case_temp WHERE case_id = %s
        """, (case_id,))
        if len(data) == 0:
            raise ValueError("`case_id` does not exist")
        is_temp=True

    db.close()
    return data[0]['asp_code'], is_temp


def db_delete_law(law_id):
    db = DatabaseAPI('nl2logic')

    # Check if law exists or not
    law_id_num = db.query(f"""
    SELECT id, law_id FROM data_law WHERE law_id = %s
    """, (law_id,))
    if len(law_id_num) == 0:
        return
    law_id_num = law_id_num[0]['id'] # numerical Id for law

    # backup law-related cases
    case_for_law = db.query(f"""
    SELECT case_id, law_id FROM rel_case_law WHERE law_id = %s 
    """, (law_id_num,))
    case_for_law = [rel['case_id'] for rel in case_for_law]

    # Delete law data with law_id
    db.query(f"""
    DELETE FROM data_law WHERE law_id = %s
    """, (law_id,))

    # by cascade, rel_law_* is auto-removed.
    # remove orphaned terms/conclusions.
    db.query(f"""
    DELETE FROM text_comment WHERE law_id NOT IN (SELECT id FROM data_law)
    """)
    db.query(f"""
    DELETE FROM asp_term
          WHERE asp_term.id NOT IN (SELECT term_id FROM rel_text_term)
    """)

    db.close()
    return case_for_law

def db_insert_law(data, case_for_law=None):
    db = DatabaseAPI('nl2logic')

    # Case ID
    law_id_text = data['lawname']

    # generate ASP from form data
    full_asp = json.dumps(data, ensure_ascii=False)

    # Add law data with law_id / ASP code
    db.query(f"""
    INSERT INTO data_law (law_id, asp_code) VALUES (%s, %s)
    """, (law_id_text, full_asp))
    law_id = db.query(f"""
        SELECT id, law_id FROM data_law WHERE law_id = %s
    """, (law_id_text,))[0]['id']

    # Add term data into DB
    term_ids = []
    for term in data['terms']:
        db.query("""
            INSERT IGNORE INTO asp_term (term) VALUES (%s)
        """, term['asp'])
        term_id = db.query(f"""
            SELECT id, term FROM asp_term WHERE term = %s
        """, term['asp'])[0]['id']
        assert term_id is not None
        term_ids.append(term_id)

    # Add comments data into DB
    nl_term_ids = []
    for term in data['terms']:
        db.query(f"""
            INSERT INTO text_comment (text, source, law_id) VALUES (%s, %s, %s)
        """, (term['comment'], term['source'], law_id))
        nl_term_id = db.query(f"""
            SELECT id, text, law_id FROM text_comment WHERE text = %s AND law_id = %s
        """, (term['comment'], law_id))[0]['id']
        nl_term_ids.append(nl_term_id)
    
    
    # Add appropriate relations
    if case_for_law:
        for case_id in case_for_law:
            db.query(f"""
            INSERT INTO rel_case_law (case_id, law_id) VALUES (%s, %s)
            """, (case_id, law_id))
    for text_id, term_id in zip(nl_term_ids, term_ids):
        db.query(f"""
        INSERT INTO rel_text_term (text_id, term_id) VALUES (%s, %s)
        """, (text_id, term_id))

    # Add term<->const relations
    for term, term_id in zip(data['terms'], term_ids):
        term_asp = term['asp']
        # extract constants
        const_list = list(set(asp_extract_const_list(term_asp)))
        const_list = [f"'{name}'" for name, arity in const_list]
        # retrieve const ids
        const_ids = db.query(f"""
        SELECT id, const FROM asp_const WHERE const IN ({', '.join(const_list)})
        """)
        const_ids = [x['id'] for x in const_ids]
        if len(const_list) != len(const_ids):
            raise ValueError("len(const_list) != len(const_ids)")
        assert len(const_list) == len(const_ids)
        # add relation
        for const_id in const_ids:
            db.query(f"""
            INSERT INTO rel_term_const (term_id, const_id) VALUES (%s, %s)
            """, (term_id, const_id))
    db.close()


def db_get_asp_body_from_law_id(law_id) :
    db = DatabaseAPI('nl2logic')

    data = db.query(f"""
    SELECT * FROM data_law WHERE law_id = %s
    """, (law_id,))
    if len(data) == 0:
        raise ValueError("`law_id` does not exist")

    db.close()
    return data[0]['asp_code']

def db_get_law_from_case(case_id, temp=False):
    db = DatabaseAPI('nl2logic')

    if temp:
        id = db.query(f"""
        SELECT id FROM data_case_temp WHERE case_id = %s
        """, (case_id,))[0]['id']
        law_ids = db.query(f"""
        SELECT law_id FROM rel_case_law_temp WHERE case_id = %s
        """, (id,))
    else:
        id = db.query(f"""
        SELECT id FROM data_case WHERE case_id = %s
        """, (case_id,))[0]['id']
        law_ids = db.query(f"""
        SELECT law_id FROM rel_case_law WHERE case_id = %s
        """, (id,))
    law_ids = [str(l['law_id']) for l in law_ids]

    if len(law_ids) > 0:
        law_names = db.query(f"""
        SELECT law_id FROM data_law WHERE id IN ({','.join(law_ids)})
        """)
        law_names = [l['law_id'] for l in law_names]

        db.close()
        return law_names
    else:
        db.close()
        return []

def db_get_all_asp_tagged_case():
    # Search for all asp_tagged case, mostly used for Langchain application
    db = DatabaseAPI('nl2logic')
    case_list = db.query("""
    SELECT * FROM data_case
    """) # List of Dict
    case_ids = ['"' + case["case_id"] + '"' for case in case_list]

    raw_case_data = db.query(f"""
    SELECT * FROM data_raw_case_info WHERE case_id IN ({','.join(case_ids)})
    """)
    raw_case_data_dict = dict()
    for raw_case in raw_case_data:
        raw_case_data_dict[raw_case["case_id"]] = raw_case
    
    for case in case_list:
        case.update(raw_case_data_dict[case["case_id"]])

    db.close()
    return case_list

def db_get_head_matching_terms(head: str) :
    db = DatabaseAPI('nl2logic')
    
    data = db.query("""
    SELECT nl_description.text AS comment,asp_term.term AS asp, nl_description.source AS source FROM
    ((nl2logic.text_comment nl_description JOIN nl2logic.rel_text_term rt ON ((nl_description.id = rt.text_id))) JOIN nl2logic.asp_term asp_term ON ((rt.term_id = asp_term.id))) WHERE (asp_term.term REGEXP %s)
    """, (head + r"[^a-z0-9].*"))

    db.close()
    return data

def db_get_random_terms(max_n: int) :
    db = DatabaseAPI('nl2logic')

    data = db.query("""
    SELECT nl_description.text AS comment,asp_term.term AS asp, nl_description.source AS source FROM
    ((nl2logic.text_comment nl_description JOIN nl2logic.rel_text_term rt ON ((nl_description.id = rt.text_id))) JOIN nl2logic.asp_term asp_term ON ((rt.term_id = asp_term.id)))
    """)

    db.close()
    return random.sample(data, max_n)

def db_get_const_information(consts):
    db = DatabaseAPI('nl2logic')

    consts = [f'"{c}"' for c in consts]
    data = db.query(f"""
    SELECT * FROM asp_const WHERE const IN ({','.join(consts)})
    """)
    db.close()
    return data
    
def db_get_all_consts():
    db = DatabaseAPI('nl2logic')
    data = db.query(f"""
    SELECT * FROM asp_const
    """)
    db.close()
    return data

def db_get_entity_relation():
    db = DatabaseAPI('nl2logic')

    data = db.query(f"""
    SELECT * FROM rel_is_a
    """)

    db.close()
    return data