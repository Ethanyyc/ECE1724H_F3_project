"""RQ4: is it practical? T8 (cost per stage) and T9 (Z3 unknown and timeout rates),
with Exp 3's writer shown apart when Exp 3 was run."""

import pandas as pd

from analysis.load import GROUPS, mean_or_none
from speccheck.checks import CHECKS, UNDETERMINED


def _exp3_name(data):
    models = data.extra_writer_specs["model"].dropna().unique()
    return f"Exp 3 ({', '.join(models) or 'unknown'})"


def _stage_rows(name, specs, attacks, repairs):
    def avg(frame, column):
        return mean_or_none(frame[column]) if (not frame.empty and column in frame) else None

    checked = specs[specs["format_ok"] == True] if not specs.empty else specs   # noqa: E712
    return [
        {"Stage": "first spec", "Metric": "LLM cost per spec (USD)", name: avg(specs, "cost_usd")},
        {"Stage": "first spec", "Metric": "input tokens per spec", name: avg(specs, "tokens_in")},
        {"Stage": "first spec", "Metric": "output tokens per spec (incl. thinking)", name: avg(specs, "tokens_out")},
        {"Stage": "first spec", "Metric": "thinking tokens per spec", name: avg(specs, "tokens_thinking")},
        {"Stage": "first spec", "Metric": "LLM latency per spec (ms)", name: avg(specs, "latency_ms")},
        {"Stage": "first spec", "Metric": "Z3 time per checked spec (ms)", name: avg(checked, "z3_time_ms")},
        {"Stage": "attack", "Metric": "LLM cost per attack (USD)", name: avg(attacks, "cost_usd")},
        {"Stage": "attack", "Metric": "attempts per attack", name: avg(attacks, "attempts_used")},
        {"Stage": "attack", "Metric": "thinking tokens per attack", name: avg(attacks, "tokens_thinking")},
        {"Stage": "attack", "Metric": "Z3 time per attack (ms)", name: avg(attacks, "z3_time_ms")},
        {"Stage": "attack", "Metric": "wall time per attack (ms)", name: avg(attacks, "wall_time_ms")},
        {"Stage": "repair", "Metric": "LLM cost per repair run (USD, incl. attacks)", name: avg(repairs, "cost_usd")},
        {"Stage": "repair", "Metric": "thinking tokens per repair run", name: avg(repairs, "tokens_thinking")},
        {"Stage": "repair", "Metric": "Z3 time per repair run (ms)", name: avg(repairs, "z3_time_ms")},
        {"Stage": "repair", "Metric": "wall time per repair run (ms)", name: avg(repairs, "wall_time_ms")},
    ]


def _by(frame, group):
    return frame[frame["group"] == group] if not frame.empty else frame


def t8_cost(data):
    specs, attacks, repairs = data.first_specs, data.exp1_attacks, data.repairs
    if specs.empty:
        return data.save("T8_cost", pd.DataFrame(), "T8. Cost per spec and stage (RQ4)")
    columns = [(f"Group {g}", _by(specs, g), _by(attacks, g), _by(repairs, g)) for g in GROUPS]
    columns.append(("All", specs, attacks, repairs))
    extra = data.extra_writer_specs
    if not extra.empty:
        columns.append((_exp3_name(data), extra, pd.DataFrame(), pd.DataFrame()))
    rows = None
    for name, s, a, r in columns:
        part = _stage_rows(name, s, a, r)
        if rows is None:
            rows = part
        else:
            for row, new in zip(rows, part):
                row[name] = new[name]
    table = pd.DataFrame(rows)
    total = (specs["cost_usd"].sum() + (attacks["cost_usd"].sum() if not attacks.empty else 0)
             + (repairs["cost_usd"].sum() if not repairs.empty else 0))
    notes = [f"Total LLM cost of Exp 1 and Exp 2: ${total:.2f} (repair runs include the attacks run inside them; "
             "the Exp 1 attack reused in type-3 round 1 is counted once, in Exp 1)."]
    if not extra.empty:
        notes.append(f"{_exp3_name(data)}: {len(extra)} first specs for ${extra['cost_usd'].sum():.2f} in total; "
                     "it writes first specs only (no attacks or repairs), and is not part of the group columns.")
    notes.append("Output tokens are the billed output and include thinking tokens; thinking tokens are shown when "
                 "the API reports them. Costs use the prices in speccheck/config.py.")
    return data.save("T8_cost", table, "T8. Cost per spec and stage (RQ4)", notes)


def _unknown_rows(specs, writer):
    checked = specs[specs["format_ok"] == True]   # noqa: E712
    rows = []
    for kind, part in (("Integer tasks", checked[checked["has_array"] == False]),   # noqa: E712
                       ("Array tasks", checked[checked["has_array"] == True])):    # noqa: E712
        row = {"Specs": writer, "Tasks": kind, "Checked specs": len(part)}
        for name in CHECKS:
            statuses = [c[name]["status"] for c in part["checks"]]
            undecided = sum(1 for s in statuses if s in ("unknown", "timeout"))
            row[f"{name}: unknown or timeout"] = f"{undecided}/{len(statuses)}"
        statuses = [e["status"] for e in part["equivalence"]]
        row["equivalence: unknown or timeout"] = f"{sum(1 for s in statuses if s in ('unknown', 'timeout'))}/{len(statuses)}"
        row["Undetermined specs"] = sum(1 for labels in part["labels"] if labels == [UNDETERMINED])
        row["Cross-check disagreements"] = int((part["cross_check_ok"] == False).sum())   # noqa: E712
        rows.append(row)
    return rows


def t9_unknowns(data):
    specs = data.specs
    if specs.empty:
        return data.save("T9_z3_unknowns", pd.DataFrame(), "T9. Z3 unknown and timeout rates (RQ4)")
    rows = _unknown_rows(specs, "Exp 1 and Exp 2")
    if not data.extra_writer_specs.empty:
        rows += _unknown_rows(data.extra_writer_specs, _exp3_name(data))
    attacks = data.attacks
    attempts = [a for run in attacks["attempts"] for a in run] if not attacks.empty else []
    notes = [f"All spec records with valid code (Exp 1 and Exp 2: first and revised specs). Attacker attempts with "
             f"an undetermined Z3 check: {sum(1 for a in attempts if a['rejected_reason'] == 'Z3 undetermined')} "
             f"of {len(attempts)}."]
    return data.save("T9_z3_unknowns", pd.DataFrame(rows), "T9. Z3 unknown and timeout rates (RQ4)", notes)
