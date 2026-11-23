"""RQ2: how good is the attacker? T4 (success, attempts, size)."""

from collections import Counter

import pandas as pd

from analysis.load import GROUPS, mean_or_none, median_range, percent
from speccheck.checks import TOO_WEAK

REASONS = ["did not follow the format", "did not pass the spec", "was actually correct", "Z3 undetermined"]


def _row(name, attacks):
    successes = attacks[attacks["success"] == True]   # noqa: E712 - pandas comparison
    reasons = Counter(a["rejected_reason"] for attempts in attacks["attempts"] for a in attempts
                      if a["rejected_reason"])
    row = {
        "Group": name,
        "Attacked": len(attacks),
        "Confirmed wrong program": f"{len(successes)} ({percent(len(successes), len(attacks))})",
        "Mean attempts (successes)": mean_or_none(successes["attempts_used"]),
        "Program size: median (range)": median_range(successes["program_size"]),
        "Source size: median (range)": median_range(successes["source_size"]),
        "No passing program exists": int((attacks["no_passing_program"] == "sat").sum()),
        "Realizability unknown": int(attacks["no_passing_program"].isin(["unknown", "timeout"]).sum()),
    }
    for reason in REASONS:
        row[f"Rejected: {reason}"] = reasons.get(reason, 0)
    return row


def t4_attacker(data):
    attacks = data.exp1_attacks
    if attacks.empty:
        return data.save("T4_attacker", pd.DataFrame(), "T4. Attacker on too-weak first specs (RQ2)")
    rows = [_row(f"Group {g}", attacks[attacks["group"] == g]) for g in GROUPS if (attacks["group"] == g).any()]
    rows.append(_row("All", attacks))
    for label, part in (("Integer tasks", attacks[attacks["has_array"] == False]),   # noqa: E712
                        ("Array tasks", attacks[attacks["has_array"] == True])):     # noqa: E712
        if len(part):
            rows.append(_row(label, part))
    specs = data.first_specs
    weak = sum(1 for labels in specs["labels"] if TOO_WEAK in labels) if not specs.empty else 0
    notes = [f"Too-weak first specs in Exp 1: {weak}; attacked: {len(attacks)} (they should be equal). "
             "Program size: distinct subterms of the Z3 expression after unrolling; source size: AST nodes. "
             "'No passing program exists' counts failed attacks whose realizability query was sat."]
    return data.save("T4_attacker", pd.DataFrame(rows), "T4. Attacker on too-weak first specs (RQ2)", notes)

