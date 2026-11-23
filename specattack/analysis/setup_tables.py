"""T1: benchmark summary."""

import pandas as pd

import benchmarks
from analysis.load import GROUP_NAMES, GROUPS


def t1_benchmarks(data):
    rows = []
    for group in GROUPS:
        tasks = [t for t in benchmarks.ALL_TASKS if t.group == group]
        rows.append({
            "Group": group,
            "Kind": GROUP_NAMES[group],
            "Tasks": len(tasks),
            "With arrays": sum(1 for t in tasks if t.has_array),
            "One answer": sum(1 for t in tasks if t.one_answer),
            "Many answers": sum(1 for t in tasks if not t.one_answer),
            "Hand-picked cases": sum(len(t.cases) for t in tasks),
            "Task ids": ", ".join(t.id for t in tasks),
        })
    return data.save("T1_benchmarks", pd.DataFrame(rows), "T1. Benchmark summary")
