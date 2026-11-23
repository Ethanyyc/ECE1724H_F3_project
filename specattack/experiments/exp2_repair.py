"""Exp 2: repair (RQ3).

Starts from every too-weak first spec in the Exp 1 log and runs the repair
loop once per feedback type. Records go to <results>/logs/exp2.jsonl.
"""

import sys
from collections import Counter
from pathlib import Path

import benchmarks
from experiments.common import Progress, clients, parser
from speccheck import config
from speccheck.checks import TOO_WEAK
from speccheck.log import RunLogger, read_jsonl
from speccheck.repair import run_repair


def select_start_specs(exp1_records, task_ids=None):
    """Too-weak first specs to repair, in benchmark order."""
    specs = [r for r in exp1_records if r["record_type"] == "spec" and r["source"] == "first"
             and r["format_ok"] and TOO_WEAK in r["labels"]]
    if task_ids:
        specs = [s for s in specs if s["task_id"] in set(task_ids)]
    order = {task.id: index for index, task in enumerate(benchmarks.ALL_TASKS)}
    return sorted(specs, key=lambda s: (order[s["task_id"]], s["repeat"]))


def _describe_outcome(record):
    rounds = record["rounds_used"]
    if record["outcome"] == "correct":
        return f"correct after {record['rounds_to_correct']} round(s)"
    if record["outcome"] == "undetermined":
        return f"undetermined in round {rounds} (Z3 could not decide)"
    return f"incorrect, all {rounds} rounds failed"


def main(argv=None):
    args = parser("Exp 2: repair loop with three feedback types.").parse_args(argv)
    exp1_log = Path(args.results_dir) / "logs" / "exp1.jsonl"
    records = read_jsonl(exp1_log)
    if not records:
        sys.exit(f"no Exp 1 log at {exp1_log}; run experiments.exp1_first_specs first")
    start_specs = select_start_specs(records, args.tasks)
    attacks = {r["spec_id"]: r for r in records if r["record_type"] == "attack" and r["context"] == "exp1"}
    writer, attacker_llm = clients(args)
    logger = RunLogger(args.results_dir, "exp2", settings={
        "start_spec_ids": [s["spec_id"] for s in start_specs],
        "exp1_run_id": records[0]["run_id"]})
    outcomes = Counter()
    progress = Progress("Exp 2", len(start_specs) * len(config.FEEDBACK_TYPES))
    for start in start_specs:
        task = benchmarks.get(start["task_id"])
        for feedback_type in config.FEEDBACK_TYPES:
            start_attack = attacks.get(start["spec_id"]) if feedback_type == 3 else None
            record = run_repair(task, start, feedback_type, writer, attacker_llm, logger, start_attack=start_attack)
            logger.write("repair", record)
            outcomes[(feedback_type, record["outcome"])] += 1
            progress.item(f"[Group {task.group}] {record['repair_id']}: {_describe_outcome(record)}")
    progress.finish()
    print(f"\nExp 2 done: {len(start_specs)} starting spec(s); outcomes {dict(outcomes)}")
    print(f"log: {logger.path}")


if __name__ == "__main__":
    main()
