"""Run Exp 1, Exp 2, Exp 3 and the analysis in order.

Usage:
    python run_all.py                 # needs API credentials, see README
Extra options (--tasks ...) are passed to every step. Replies saved by earlier
runs are reused, so only calls not made before cost anything; --fresh asks the
LLM again for every call (a new sample). After
changing a task, a golden reference or the checking code, run the tests first.
"""

import argparse
import subprocess
import sys
import time

from experiments.common import format_duration


def main():
    p = argparse.ArgumentParser(description="Run Exp 1, Exp 2, Exp 3 and the analysis.")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--tasks", nargs="*")
    p.add_argument("--fresh", action="store_true", help="ask the LLM again instead of reusing saved replies")
    args = p.parse_args()
    common = ["--results-dir", args.results_dir] + (["--tasks", *args.tasks] if args.tasks else [])
    llm = ["--fresh"] if args.fresh else []
    steps = [("Exp 1: first specs, checks and attacks", ["experiments.exp1_first_specs", *common, *llm]),
             ("Exp 2: repair with three feedback types", ["experiments.exp2_repair", *common, *llm]),
             ("Exp 3: first specs from a more capable writer", ["experiments.exp3_writer_comparison", *common, *llm]),
             ("Analysis: tables and figures", ["analysis.run_analysis", "--results-dir", args.results_dir])]
    started = time.perf_counter()
    for number, (title, step) in enumerate(steps, start=1):
        print(f"\n=== [{number}/{len(steps)}] {title}\n    python -m {' '.join(step)}", flush=True)
        step_started = time.perf_counter()
        if subprocess.run([sys.executable, "-m", *step]).returncode != 0:
            sys.exit(f"step failed: {step[0]}")
        print(f"=== [{number}/{len(steps)}] finished in {format_duration(time.perf_counter() - step_started)}",
              flush=True)
    print(f"\nAll {len(steps)} steps finished in {format_duration(time.perf_counter() - started)}")


if __name__ == "__main__":
    main()
