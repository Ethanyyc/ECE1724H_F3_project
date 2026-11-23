"""Read the experiment logs into pandas tables, and write tables to disk."""

from math import comb
from pathlib import Path

import pandas as pd

from speccheck.log import read_jsonl

GROUPS = (1, 2, 3, 4)
GROUP_NAMES = {1: "integer functions", 2: "array problems", 3: "many correct answers", 4: "AI-generated, very hard"}


class Data:
    """specs, attacks and repairs from logs/exp1.jsonl and logs/exp2.jsonl; the specs of
    Exp 3 (logs/exp3.jsonl, another writer) are kept apart in extra_writer_specs."""

    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)
        logs = self.results_dir / "logs"
        records = []
        for experiment in ("exp1", "exp2"):
            for record in read_jsonl(logs / f"{experiment}.jsonl"):
                record["experiment"] = experiment
                records.append(record)
        self.specs = _frame([r for r in records if r["record_type"] == "spec"])
        self.attacks = _frame([r for r in records if r["record_type"] == "attack"])
        self.repairs = _frame([r for r in records if r["record_type"] == "repair"])
        self.extra_writer_specs = _frame([r for r in read_jsonl(logs / "exp3.jsonl") if r["record_type"] == "spec"])
        self.tables = self.results_dir / "tables"
        self.figures = self.results_dir / "figures"
        self.tables.mkdir(parents=True, exist_ok=True)
        self.figures.mkdir(parents=True, exist_ok=True)

    @property
    def first_specs(self):
        if self.specs.empty:
            return self.specs
        return self.specs[(self.specs["experiment"] == "exp1") & (self.specs["source"] == "first")]

    @property
    def exp1_attacks(self):
        if self.attacks.empty:
            return self.attacks
        return self.attacks[self.attacks["context"] == "exp1"]

    def save(self, name, frame, title, notes=()):
        """Write <tables>/<name>.csv and <name>.md."""
        frame.to_csv(self.tables / f"{name}.csv", index=False)
        lines = [f"# {title}", "", markdown(frame)]
        if notes:
            lines += [""] + [f"{note}" for note in notes]
        (self.tables / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.tables / f"{name}.md"


def _frame(records):
    return pd.DataFrame(records) if records else pd.DataFrame()


def markdown(frame):
    if frame.empty:
        return "(no data)"
    columns = [str(c) for c in frame.columns]
    rows = [[_cell(v) for v in row] for row in frame.itertuples(index=False, name=None)]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:   # NaN
            return ""
        return f"{value:.4g}"
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def percent(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else ""


def mean_or_none(series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else None


def median_range(series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    if not len(values):
        return ""
    return f"{values.median():g} ({values.min():g}-{values.max():g})"


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value for b and c discordant pairs."""
    n = b + c
    if n == 0:
        return None
    tail = sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)
