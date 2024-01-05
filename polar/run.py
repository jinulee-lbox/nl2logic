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
    startdate = datetime.now().strftime('%Y%m%d-%H:%M:%S')

    dataset = args.dataset
    
    logging.info(f"DATASET: {dataset}")

    dataset = PolarContext(config, dataset)
    logging.info("==============================\n")
    logging.info("PROMPT:")
    for func, prompt in dataset.prompt_data.items():
        logging.info(f"- {func}\n{prompt}\n")
    results = []
    for datum in dataset.test_data:
        logging.info("==============================\n")
        logging.info(f"{json.dumps(datum, indent=4, ensure_ascii=False)}\n\n")
        logging.info("- - - - - - - - - - - - - - -")
        result, program = generate_abductive_proof(datum, dataset)
        logging.info("\n" + str(result) + "\n")
        logging.info(json.dumps(program, indent=4, ensure_ascii=False) + "\n\n")
        results.append({
            "test_data": datum,
            "program": program
        })
        correctness = datum['label'] == (result is not None) # A goal is solved
        if result is not None and datum['label'] == True and 'goal_solved' in datum:
            # If the task is to find an unknown value by reasoning,
            correctness = datum['goal_solved'] == result.root.repr
        logging.info(f"Did the model got correct? {correctness}")
        
        # Find the diff of golden and generated program
        gold_set = set([x['asp'] for x in datum['program']])
        model_set = set([x['asp'] for x in program])
        logging.info("Statements in gold / not in model output:")
        for x in gold_set.difference(model_set):
            logging.info(f"- {x}")
        logging.info("Statements in model output / not in gold:")
        for x in model_set.difference(gold_set):
            logging.info(f"- {x}")
    
    result_dir = f"logs/polar_{startdate}_{args.dataset}_result.json"
    with open(result_dir, "w", encoding="UTF-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Dataset ID.", choices=config.polar.datasets.__dict__.keys())
    args = parser.parse_args()
    main(args)