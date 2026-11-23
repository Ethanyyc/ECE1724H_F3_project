"""Generate every table and chart from the logs.

Usage: python -m analysis.run_analysis [--results-dir results]
"""

import argparse

from analysis import rq1, rq2, rq3, rq4, setup_tables
from analysis.load import Data
from speccheck import config


def run(results_dir):
    data = Data(results_dir)
    return [
        setup_tables.t1_benchmarks(data),
        rq1.t2_labels(data),
        rq2.t4_attacker(data),
        rq3.t6_repair(data),
        rq3.f1_rounds(data),
        rq3.f2_repair(data),
        rq3.t7_pairwise(data),
        rq4.t8_cost(data),
        rq4.t9_unknowns(data),
        rq1.t10_writer_comparison(data),
    ]


def main(argv=None):
    p = argparse.ArgumentParser(description="Tables and charts from the experiment logs.")
    p.add_argument("--results-dir", default=str(config.DEFAULT_RESULTS_DIR))
    args = p.parse_args(argv)
    for path in run(args.results_dir):
        print(path)


if __name__ == "__main__":
    main()
