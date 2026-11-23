"""Exp 1: checking first specs (RQ1, RQ2, RQ4).

For every task and repeat, the spec writer writes a first spec; it goes
through the format check, the four checks and the equivalence cross-check;
every too-weak spec is attacked. Records go to <results>/logs/exp1.jsonl.
"""

from collections import Counter

from experiments.common import Progress, clients, first_spec_id, parser, tasks
from speccheck import config, prompting
from speccheck.attacker import attack
from speccheck.checks import TOO_WEAK, try_check_spec
from speccheck.loader import LoadedSpec, load_spec
from speccheck.log import RunLogger
from speccheck.records import spec_record


def run_first_spec(task, repeat, writer, attacker_llm, logger):
    """Write, check and (if too weak and attacker_llm is given) attack one first spec.
    Returns (spec record, attack record or None)."""
    spec_id = first_spec_id(task.id, repeat)
    result = writer.complete(prompting.spec_writer(task), tag=f"exp1:{task.id}:r{repeat}")
    loaded = load_spec(result.text, task)
    check = None
    if loaded.ok:
        check, error = try_check_spec(task, loaded)
        if error:
            loaded = LoadedSpec(False, error, loaded.code, loaded.pre_code, loaded.post_code)
    record = spec_record(spec_id, task, "first", repeat, None, result, loaded, check)
    logger.write("spec", record)
    attack_record = None
    if attacker_llm is not None and check is not None and TOO_WEAK in check["labels"]:
        attack_record = attack(task, loaded, loaded.code, check["checks"]["weak"]["example"], attacker_llm,
                               tag=f"exp1:{spec_id}:attack", context="exp1",
                               attack_id=f"{spec_id}:attack", spec_id=spec_id)
        logger.write("attack", attack_record)
    return record, attack_record


def main(argv=None):
    p = parser("Exp 1: first specs, checks and attacks.")
    p.add_argument("--repeats", type=int, default=config.REPEATS)
    args = p.parse_args(argv)
    selected = tasks(args)
    writer, attacker_llm = clients(args)
    logger = RunLogger(args.results_dir, "exp1", settings={"repeats": args.repeats,
                                                            "tasks": [t.id for t in selected]})
    labels, attacks, mismatches = Counter(), Counter(), []
    progress = Progress("Exp 1", len(selected) * args.repeats)
    for task in selected:
        for repeat in range(args.repeats):
            record, attack_record = run_first_spec(task, repeat, writer, attacker_llm, logger)
            labels.update(record["labels"])
            if record["cross_check_ok"] is False:
                mismatches.append(record["spec_id"])
            outcome = ""
            if attack_record is not None:
                attacks["success" if attack_record["success"] else "failed"] += 1
                outcome = " | attack " + ("succeeded" if attack_record["success"] else "failed")
            progress.item(f"[Group {task.group}] {record['spec_id']}: {', '.join(record['labels'])}{outcome}")
    progress.finish()
    print(f"\nExp 1 done: {sum(labels.values())} label(s) {dict(labels)}; attacks {dict(attacks)}")
    print(f"log: {logger.path}")
    if mismatches:
        print(f"WARNING: the equivalence cross-check disagreed with the four checks on {mismatches}")


if __name__ == "__main__":
    main()
