"""RQ1: how common are bad specs? T2 (labels of first specs) and T10 (the default
writer against a more capable one, from Exp 3)."""

import pandas as pd

from analysis.load import GROUPS
from speccheck.checks import DEFECT_LABELS, FORMAT_FAILURE, LABEL_ORDER

LLM_ERROR_ROW = "LLM error (a defect, or did not follow the format)"
LLM_ERROR_LABELS = set(DEFECT_LABELS) | {FORMAT_FAILURE}


def _shares(frame, wanted):
    """Share of specs with any of the labels in `wanted` for each repeat: list of fractions."""
    shares = []
    for _, part in frame.groupby("repeat"):
        shares.append(sum(1 for labels in part["labels"] if wanted & set(labels)) / len(part))
    return shares


def _cell(shares):
    if not shares:
        return ""
    mean = sum(shares) / len(shares)
    low, high = min(shares), max(shares)
    if len(shares) == 1 or low == high:
        return f"{100 * mean:.0f}%"
    return f"{100 * mean:.0f}% ({100 * low:.0f}-{100 * high:.0f})"


def t2_labels(data):
    specs = data.first_specs
    if specs.empty:
        return data.save("T2_first_spec_labels", pd.DataFrame(), "T2. Labels of first specs")
    columns = {f"Group {g}": specs[specs["group"] == g] for g in GROUPS}
    columns["All"] = specs
    rows = []
    for label, wanted in [(label, {label}) for label in LABEL_ORDER] + [(LLM_ERROR_ROW, LLM_ERROR_LABELS)]:
        row = {"Label": label}
        for name, part in columns.items():
            row[name] = _cell(_shares(part, wanted)) if len(part) else ""
        rows.append(row)
    repeats = sorted(int(r) for r in specs["repeat"].unique())
    count_row = {"Label": "specs per repeat" if len(repeats) > 1 else "specs"}
    for name, part in columns.items():
        count_row[name] = str(len(part) // max(1, part["repeat"].nunique())) if len(part) else "0"
    rows.append(count_row)
    share = (f"Mean share over repeats {repeats}, with the minimum and maximum over repeats in parentheses. "
             if len(repeats) > 1 else "Share of first specs with each label. ")
    notes = [share + "A spec can have several defect labels, so a column can add up to more than 100%. "
             "Undetermined specs (a Z3 query timed out or returned unknown, with no definite problem) "
             "are listed separately and are not counted as defects.",
             f"'{LLM_ERROR_ROW}': the spec is wrong or its code does not run; each spec counts once."]
    return data.save("T2_first_spec_labels", pd.DataFrame(rows), "T2. Labels of first specs (RQ1)", notes)


def _writer(specs, experiment):
    models = specs["model"].dropna().unique() if "model" in specs else []
    return f"{', '.join(models) or 'unknown'} ({experiment})"


def _error_counts(specs):
    """LLM errors per task: {task_id: (errors, specs)}."""
    return {task_id: (sum(1 for labels in part["labels"] if LLM_ERROR_LABELS & set(labels)), len(part))
            for task_id, part in specs.groupby("task_id")}


def t10_writer_comparison(data):
    title = "T10. First-spec labels of the default writer (Exp 1) and a more capable writer (Exp 3) (RQ1 extension)"
    base, extra = data.first_specs, data.extra_writer_specs
    if extra.empty or base.empty:
        return data.save("T10_writer_comparison", pd.DataFrame(), title,
                         ["No Exp 1 or Exp 3 log yet: run python run_all.py (or the missing experiment, "
                          "then python -m analysis.run_analysis)."])
    shared = set(base["task_id"]) & set(extra["task_id"])
    base, extra = base[base["task_id"].isin(shared)], extra[extra["task_id"].isin(shared)]
    writers = [(_writer(base, "Exp 1"), base), (_writer(extra, "Exp 3"), extra)]
    rows = []
    for group in (*GROUPS, "All"):
        for name, specs in writers:
            part = specs if group == "All" else specs[specs["group"] == group]
            if not len(part):
                continue
            row = {"Group": group, "Writer": name, "Specs": len(part)}
            for label, wanted in [(label, {label}) for label in LABEL_ORDER] + [("LLM error", LLM_ERROR_LABELS)]:
                row[label] = _cell(_shares(part, wanted))
            row["Mean cost per spec (USD)"] = round(float(part["cost_usd"].mean()), 6)
            rows.append(row)
    base_errors, extra_errors = _error_counts(base), _error_counts(extra)

    def listed(task_ids, counts):
        return ", ".join(f"{t} ({counts[t][0]}/{counts[t][1]})" for t in sorted(task_ids)) or "none"

    wrong_base = {t for t, (errors, _) in base_errors.items() if errors}
    wrong_extra = {t for t, (errors, _) in extra_errors.items() if errors}
    notes = [f"Both runs on the same {len(shared)} tasks, with the same prompt, repeats and checks; only the writer "
             "model differs. Shares as in T2; 'LLM error' is a defect or a format failure.",
             f"Tasks with LLM errors only for {writers[0][0]}: {listed(wrong_base - wrong_extra, base_errors)}.",
             f"Tasks with LLM errors only for {writers[1][0]}: {listed(wrong_extra - wrong_base, extra_errors)}.",
             "Tasks with LLM errors for both (Exp 1 vs Exp 3): " + (", ".join(
                 f"{t} ({base_errors[t][0]}/{base_errors[t][1]} vs {extra_errors[t][0]}/{extra_errors[t][1]})"
                 for t in sorted(wrong_base & wrong_extra)) or "none") + "."]
    return data.save("T10_writer_comparison", pd.DataFrame(rows), title, notes)

