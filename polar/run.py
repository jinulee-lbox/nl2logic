import json
import random
import logging
import argparse
from datetime import datetime

from nl2logic.config import set_logger
from polar.chain.generate_abductive_proof import generate_abductive_proof

from polar.chain.utils import config, PolarContext


NUM_PER_CASE = 20

def main(args):
    random.seed(41)
    set_logger("polar", dataset=args.dataset)

    dataset = args.dataset
    
    logging.info(f"DATASET: {dataset}")

    dataset = PolarContext(config, dataset)
    results = []
    for datum in dataset.test_data[:100]:
        print(json.dumps(datum, indent=4, ensure_ascii=False))
        result, program = generate_abductive_proof(datum, dataset)
        logging.info("==============================\n")
        logging.info(f"{json.dumps(datum, indent=4, ensure_ascii=False)}\n\n")
        logging.info("\n" + str(result) + "\n")
        logging.info(json.dumps(program, indent=4, ensure_ascii=False) + "\n\n")
        results.append({
            "test_data": datum,
            "program": program
        })
        logging.info(f"Did the model got correct? {datum['label'] == (result is not None)}")
    
    result_dir = f"logs/polar_{datetime.now().strftime('%Y%m%d-%H:%M:%S')}_{args.dataset}_result.json"
    with open(result_dir, "w", encoding="UTF-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Dataset ID.", choices=config.polar.datasets.__dict__.keys())
    args = parser.parse_args()
    main(args)