import json
from typing import Dict

from langchain.prompts import SemanticSimilarityExampleSelector
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from nl2logic.database_utils.queries import db_get_all_asp_tagged_case, db_get_asp_body_from_case_id
from nl2logic.config import nl2logic_config as config

# these three lines swap the stdlib sqlite3 lib with the pysqlite3 package
# https://gist.github.com/defulmere/8b9695e415a44271061cc8e272f3c300
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# Retrieve example from DB
_examples = db_get_all_asp_tagged_case()

# Add term data
_examples_dict = dict()
for example in _examples:
    case_id = example["case_id"]
    data, _  = db_get_asp_body_from_case_id(case_id)
    data = json.loads(data)
    # comment_list
    example["terms"] = data["terms"]
    _examples_dict[case_id] = example # hash items for fast search

# Vectorize to Chroma
_to_vectorize = [example["body_text"] for example in _examples]
_embeddings = OpenAIEmbeddings(model=config.langchain.openai.embedding_model, openai_api_key=config.langchain.openai.api_key)
_case_ids = [{"case_id": example["case_id"]} for example in _examples]
_vectorstore = Chroma.from_texts(_to_vectorize, _embeddings, metadatas=_case_ids, persist_directory=config.langchain.chroma.persist_directory)

_case_example_selector = SemanticSimilarityExampleSelector(
    vectorstore=_vectorstore,
    k=1,
)

def case_select_examples(query: Dict[str, str]):
    assert "body_text" in query
    examples = _case_example_selector.select_examples(query)
    results = []
    for example in examples:
        results.append(_examples_dict[example["case_id"]])
    return results