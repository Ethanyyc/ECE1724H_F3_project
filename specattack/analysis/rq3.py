"""RQ3: what feedback helps? T6 (per type), F1 (fixed after each round), F2 (per round
and per group), T7 (pairwise)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import pandas as pd   # noqa: E402

from analysis.load import GROUPS, mcnemar_exact, mean_or_none, percent   # noqa: E402
from speccheck import config   # noqa: E402
from speccheck.checks import DEFECT_LABELS, FORMAT_FAILURE   # noqa: E402

TYPE_NAMES = {1: "1: pass/fail", 2: "2: one example", 3: "3: wrong program"}


def _new_defect(run):
    start = set(run["start_labels"]) & set(DEFECT_LABELS)
    for entry in run["rounds"]:
        labels = entry["labels"] or []
        if (set(labels) & set(DEFECT_LABELS)) - start:
            return True
    return False


def t6_repair(data):
    repairs = data.repairs
    if repairs.empty:
        return data.save("T6_repair", pd.DataFrame(), "T6. Repair per feedback type (RQ3)")
    rows = []
    for feedback_type in config.FEEDBACK_TYPES:
        runs = repairs[repairs["feedback_type"] == feedback_type]
        if runs.empty:
            continue
        correct = runs[runs["outcome"] == "correct"]
        rounds = [entry for run in runs["rounds"] for entry in run]
        new_defects = sum(_new_defect(r) for _, r in runs.iterrows())
        rows.append({
            "Feedback type": TYPE_NAMES[feedback_type],
            "Runs": len(runs),
            "Ended correct": f"{len(correct)} ({percent(len(correct), len(runs))})",
            "Ended undetermined": int((runs["outcome"] == "undetermined").sum()),
            "Mean rounds to correct": mean_or_none(correct["rounds_to_correct"]),
            "Runs with a new defect": f"{new_defects} ({percent(new_defects, len(runs))})",
            "Invalid replies": sum(1 for e in rounds if e["labels"] == [FORMAT_FAILURE]),
            "Rounds that fell back to the example": sum(1 for e in rounds if e["fell_back_to_example"]),
        })
    notes = ["'New defect': some revision had a defect category that the starting spec did not have "
             "(for example, it became too strong). 'Fell back': type 3 found no wrong program and reported "
             "the single example instead."]
    return data.save("T6_repair", pd.DataFrame(rows), "T6. Repair per feedback type (RQ3)", notes)


def f1_rounds(data):
    repairs = data.repairs
    path = data.figures / "F1_fixed_after_round"
    rows = []
    figure, axis = plt.subplots(figsize=(5, 3.5))
    for feedback_type in config.FEEDBACK_TYPES:
        runs = repairs[repairs["feedback_type"] == feedback_type] if not repairs.empty else repairs
        if runs.empty:
            continue
        fractions = []
        for k in range(0, config.REPAIR_ROUNDS + 1):
            fixed = sum(1 for _, r in runs.iterrows() if r["outcome"] == "correct" and r["rounds_to_correct"] <= k)
            fractions.append(fixed / len(runs))
            rows.append({"Feedback type": TYPE_NAMES[feedback_type], "Round": k, "Fraction correct": fixed / len(runs)})
        axis.plot(range(0, config.REPAIR_ROUNDS + 1), fractions, marker="o", label=TYPE_NAMES[feedback_type])
    axis.set_xlabel("Repair round")
    axis.set_ylabel("Fraction of specs correct")
    axis.set_xticks(range(0, config.REPAIR_ROUNDS + 1))
    axis.set_ylim(0, 1.05)
    axis.grid(alpha=0.3)
    if rows:
        axis.legend()
    figure.tight_layout()
    figure.savefig(path.with_suffix(".png"), dpi=200)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    data.save("F1_fixed_after_round_data", pd.DataFrame(rows), "F1 data. Cumulative fraction correct after each round")
    return path.with_suffix(".png")


def _fixed_within(runs, rounds):
    return int(((runs["outcome"] == "correct") & (runs["rounds_to_correct"] <= rounds)).sum())


def _draw_bars(axis, categories, values, labels, ylabel, ymax, title):
    """values[i][j]: bar height for category i and feedback type j; labels: text above each bar."""
    types = list(config.FEEDBACK_TYPES)
    width = 0.8 / len(types)
    for j, feedback_type in enumerate(types):
        xs = [i + (j - (len(types) - 1) / 2) * width for i in range(len(categories))]
        heights = [row[j] for row in values]
        axis.bar(xs, heights, width * 0.95, label=TYPE_NAMES[feedback_type])
        for x, height, label in zip(xs, heights, [row[j] for row in labels]):
            axis.text(x, height + ymax * 0.015, label, ha="center", va="bottom", fontsize=7.5)
    axis.set_xticks(range(len(categories)))
    axis.set_xticklabels(categories)
    axis.set_ylabel(ylabel)
    axis.set_ylim(0, ymax * 1.12)
    axis.set_title(title, fontsize=10)
    axis.grid(axis="y", alpha=0.3)
    axis.set_axisbelow(True)


def f2_repair(data):
    """(a) specs fixed by the end of each round; (b) share of each group's specs fixed in round 1."""
    repairs = data.repairs
    path = data.figures / "F2_repair"
    if repairs.empty:
        return data.save("F2_repair_data", pd.DataFrame(), "F2 data. Specs fixed per round and per group")
    types = list(config.FEEDBACK_TYPES)
    total = repairs["start_spec_id"].nunique()
    rounds = range(1, config.REPAIR_ROUNDS + 1)
    by_round = [[_fixed_within(repairs[repairs["feedback_type"] == t], k) for t in types] for k in rounds]
    rows = [{"Panel": "a", "Specs": f"all ({total})", "Round": k, "Feedback type": TYPE_NAMES[t], "Fixed": v}
            for k, row in zip(rounds, by_round) for t, v in zip(types, row)]

    parts = [(f"Group {g}", repairs[repairs["group"] == g]) for g in GROUPS if (repairs["group"] == g).any()]
    parts.append(("All", repairs))
    groups, shares, labels = [], [], []
    for name, part in parts:
        n = part["start_spec_id"].nunique()
        fixed = [_fixed_within(part[part["feedback_type"] == t], 1) for t in types]
        groups.append(f"{name}\n({n} spec{'s' if n != 1 else ''})")
        shares.append([100 * f / n for f in fixed])
        labels.append([str(f) for f in fixed])
        rows += [{"Panel": "b", "Specs": f"{name} ({n})", "Round": 1, "Feedback type": TYPE_NAMES[t], "Fixed": f}
                 for t, f in zip(types, fixed)]

    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 3.9), width_ratios=[len(rounds), len(groups)])
    _draw_bars(left, [f"after round {k}" for k in rounds], by_round, [[str(v) for v in row] for row in by_round],
               f"specs fixed (of {total})", total, f"(a) Fixed by the end of each round (all {total})")
    left.set_yticks(range(0, total + 1, 5))
    _draw_bars(right, groups, shares, labels, "fixed in round 1 (%)", 100,
               "(b) Fixed in round 1, by group (number of specs on each bar)")
    handles, names = left.get_legend_handles_labels()
    figure.legend(handles, names, fontsize=9, loc="lower center", ncol=len(types), frameon=False)
    figure.tight_layout(rect=(0, 0.07, 1, 1))
    figure.savefig(path.with_suffix(".png"), dpi=200)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    data.save("F2_repair_data", pd.DataFrame(rows), "F2 data. Specs fixed per round and per group",
              ["Panel a: specs fixed by the end of each round (a spec fixed in round k counts in every later "
               "round). Panel b: specs of each group fixed in round 1."])
    return path.with_suffix(".png")


def t7_pairwise(data):
    repairs = data.repairs
    if repairs.empty:
        return data.save("T7_pairwise", pd.DataFrame(), "T7. Fixed by one feedback type but not the other (RQ3)")
    fixed = {}
    for _, run in repairs.iterrows():
        fixed.setdefault(run["start_spec_id"], {})[run["feedback_type"]] = run["outcome"] == "correct"
    types = list(config.FEEDBACK_TYPES)
    rows = []
    for row_type in types:
        row = {"Fixed by": TYPE_NAMES[row_type]}
        for column_type in types:
            if column_type == row_type:
                row[f"not by {column_type}"] = ""
                continue
            row[f"not by {column_type}"] = sum(1 for result in fixed.values()
                                               if result.get(row_type) and result.get(column_type) is False)
        rows.append(row)
    notes = []
    for a, b in ((3, 2), (2, 1), (3, 1)):
        only_a = sum(1 for r in fixed.values() if r.get(a) and r.get(b) is False)
        only_b = sum(1 for r in fixed.values() if r.get(b) and r.get(a) is False)
        p = mcnemar_exact(only_a, only_b)
        notes.append(f"Type {a} vs type {b}: fixed only by {a}: {only_a}, only by {b}: {only_b}; "
                     f"exact McNemar p = {p:.3g}" if p is not None else
                     f"Type {a} vs type {b}: no discordant specs.")
    return data.save("T7_pairwise", pd.DataFrame(rows), "T7. Fixed by one feedback type but not the other (RQ3)",
                     notes)
