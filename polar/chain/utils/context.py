import json
import os
from pathlib import Path
from types import SimpleNamespace
# from pysolver.utils import parse_line, find_all_const

class PolarContext():
    def __init__(self, config: SimpleNamespace, dataset: str):
        self.config: SimpleNamespace = config.polar
        self.dataset: str = dataset

        dataset_dir = Path(self.config.datasets.__dict__[dataset])
        self.ontology_data = []
        self.example_data = []
        self.world_data = []
        self.test_data = None
        
        # Optional
        if "ontology_data.json" in os.listdir(dataset_dir):
            self.ontology_data = json.load(open(dataset_dir / "ontology_data.json"))
        if "example_data.json" in os.listdir(dataset_dir):
            self.example_data = json.load(open(dataset_dir / "example_data.json"))
        if "world_data.json" in os.listdir(dataset_dir):
            self.world_data = json.load(open(dataset_dir / "world_data.json"))
        # Mandatory
        self.test_data = json.load(open(dataset_dir / "test_data.json"))

        self._validate_data()
    
    def _validate_data(self):
        self._validate_ontology_data()
        self._validate_example_data()
        self._validate_world_data()
        self._validate_test_data()

    def _validate_ontology_data(self):
        data = self.ontology_data
        if data is None:
            return
        assert isinstance(data, list)
        for datum in data:
            assert isinstance(datum, dict)
            for k in ["id", "const", "nargs", "description", "lexical_unit"]:
                assert k in datum
                
    def _validate_example_data(self):
        data = self.example_data
        if data is None:
            return
        assert isinstance(data, list)
        for datum in data:
            assert isinstance(datum, dict)
            for k in ["id", "statement", "description"]:
                assert k in datum

    def _validate_world_data(self):
        data = self.world_data
        if data is None:
            return
        assert isinstance(data, list)
        for datum in data:
            assert isinstance(datum, dict)
            for k in ["id", "name", "statements"]:
                assert k in datum
            for rule in data["statements"]:
                for k in ["id", "statement", "description"]:
                    assert k in rule

    def _validate_test_data(self):
        data = self.test_data
        if data is None:
            return
        assert isinstance(data, list)
        for datum in data:
            assert isinstance(datum, dict)
            for k in ["id", "body_text", "rule_names", "goal", "label", "program"]:
                assert k in datum

    # def find_missing_ontology(self, consts: List[AST]):
    def find_missing_ontology(self, consts):
        pass