"""Exp 3 (extension of RQ1): how many first specs a more capable writer gets wrong.

Same tasks, prompt, repeats and checks as Exp 1, but the first specs are written
by config.EXTRA_WRITER_MODEL (or --model) at config.EXTRA_WRITER_THINKING_EFFORT.
Too-weak specs are not attacked or repaired. Records go to
<results>/logs/exp3.jsonl, apart from Exp 1; the analysis compares the two
writers in table T10.
"""

from collections import Counter

from experiments.common import Progress, parser, tasks, writer_client
from experiments.exp1_first_specs import run_first_spec
from speccheck import config
from speccheck.log import RunLogger


def main(argv=None):
    p = parser("Exp 3: first specs from a more capable writer (extension of RQ1).")
    p.add_argument("--model", default=config.EXTRA_WRITER_MODEL)
    p.add_argument("--effort", default=config.EXTRA_WRITER_THINKING_EFFORT)
    p.add_argument("--repeats", type=int, default=config.REPEATS)
    args = p.parse_args(argv)
    selected = tasks(args)
    writer = writer_client(args, args.model, args.effort)
    logger = RunLogger(args.results_dir, "exp3", settings={
        "repeats": args.repeats, "tasks": [t.id for t in selected],
        "writer_model": args.model, "writer_thinking_effort": args.effort})
    labels = Counter()
    progress = Progress("Exp 3", len(selected) * args.repeats)
    for task in selected:
        for repeat in range(args.repeats):
            record, _ = run_first_spec(task, repeat, writer, None, logger)
            labels.update(record["labels"])
            progress.item(f"[Group {task.group}] {record['spec_id']}: {', '.join(record['labels'])}")
    progress.finish()
    print(f"\nExp 3 done ({args.model}): {sum(labels.values())} label(s) {dict(labels)}")
    print(f"log: {logger.path}")


if __name__ == "__main__":
    main()
