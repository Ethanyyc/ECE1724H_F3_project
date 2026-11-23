# Breaking and Improving LLM-Written Specs with Program Synthesis

ECE1724H F3 (Program Synthesis and Verification), Fall 2026, term project.

Team (Group 10): Yicheng Yao (`yicheng.yao@mail.utoronto.ca`), Jarvis Wang (`jarvis.wang@mail.utoronto.ca`)

## Overview

Formal verification proves that code matches its spec, but not that the spec says what we meant. LLMs are increasingly asked to write specs, and an LLM-written spec can look fine yet be too weak (accepts wrong programs), too strong (rejects the right one), too strict on inputs, or empty.

This project builds a spec checker and repair loop:

1. An LLM writes a spec (pre- and postcondition) from a plain-English task description.
2. Z3 checks the spec for each kind of problem and returns a concrete example when it finds one.
3. An attacker writes a wrong program that still passes a too-weak spec, for example "your clamp spec accepts `return lo`". The attacker is an LLM, and Z3 confirms every program, so there are no false alarms.
4. The spec-writing LLM repairs the spec using that feedback.

Models (set in `specattack/speccheck/config.py`): Claude Haiku 5.5 (`claude-haiku-5-5`) writes and repairs specs, Claude Sonnet 5.5 (`claude-sonnet-5-5`) attacks them, and Exp 3 uses Claude Opus 5.5 (`claude-opus-5-5`) as the writer. All use adaptive thinking at medium effort; with thinking on, the API takes no custom temperature. Prices are from the November 2026 price list.

## Research questions

- RQ1: How common are bad specs written by LLMs, and what do they usually get wrong?
- RQ2: How often can the attacker turn a weak spec into a confirmed wrong program?
- RQ3: What feedback helps the LLM fix its spec: pass/fail, a single example, or a whole wrong program?
- RQ4: Is the approach practical in time and cost?

## Running the project

All commands run from the `specattack` folder. What you can do, and what it needs:

| Goal | Needs an API key? | Time |
|---|---|---|
| Run the tests (step 3) | no | under a minute |
| Regenerate every table and figure of the report from the included logs (step 4) | no | seconds |
| Rerun the experiments (steps 5 and 6) | yes | depends on the LLM; saved replies are reused |

### 1. Prerequisites

- Python 3.10 or later (developed and tested with Python 3.11).
- For the experiments only: an Anthropic API key (step 5).

### 2. Create the virtual environment and install the packages

The project uses its own Python environment in `specattack/.venv` (not included in the repository; these commands create it). The packages are listed in `specattack/requirements.txt`: z3-solver, anthropic, pandas, matplotlib and pytest.

Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
source .venv/bin/activate
```

The last line activates the environment, so that `python` in the steps below means the project's Python. Activation lasts for the current terminal only; in a new terminal, activate again. If PowerShell refuses to run `Activate.ps1`, either run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip activation and write `.\.venv\Scripts\python.exe` wherever the steps say `python`. Any installed Python from 3.10 up works in place of 3.11, for example `py -3.12`.

### 3. Run the tests

```bash
python -m pytest
```

All 338 tests should pass in under a minute. They check every golden reference (against an AI-written second Z3 formula, on hand-picked cases and with the input checks), the loader, the checks, the attacker and the repair loop. They use scripted replies and never call the API. Run them again after changing a task, a golden reference, a sample spec or the checking code.

### 4. Regenerate the report's tables and figures

```bash
python -m analysis.run_analysis
```

This reads the experiment logs included in `results/logs/` and writes `results/tables/*.md` and `*.csv` (tables T1, T2, T4, T6 to T10) and `results/figures/F1_*` and `F2_*` (PNG and PDF). It never calls an LLM, so it is the quickest way to check the numbers in the report.

### 5. Set up LLM access (for the experiments only)

The experiments call Claude through the [Anthropic API](https://docs.anthropic.com/). Create an API key in the Anthropic Console and set it as an environment variable; it is never stored in the repository. A variable set this way lasts only for the current terminal.

Windows (PowerShell):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

macOS or Linux:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Then check the connection, which makes one tiny call per model:

```bash
python -m experiments.check_api
```

It reports whether the key is set, lists the models the API offers, and should report OK for both the writer and the attacker model. The model that actually answered each call is logged as `model_version`.

### 6. Run the experiments

Run everything in order (Exp 1, Exp 2, Exp 3, then the analysis):

```bash
python run_all.py
```

Or run the steps one at a time:

| Step | Command | Output |
|---|---|---|
| Exp 1: first specs and attacks (RQ1, RQ2, RQ4) | `python -m experiments.exp1_first_specs` | `results/logs/exp1.jsonl` |
| Exp 2: repairs with each feedback type (RQ3) | `python -m experiments.exp2_repair` | `results/logs/exp2.jsonl` |
| Exp 3: first specs from a stronger writer (RQ1) | `python -m experiments.exp3_writer_comparison` | `results/logs/exp3.jsonl` |
| Analysis | `python -m analysis.run_analysis` | `results/tables/`, `results/figures/` |

Exp 2 repairs the too-weak specs of Exp 1, so run Exp 1 first. Each step prints one line per spec or repair run, for example `[  1/150]   0% [Group 1] trunc_div3-r0: correct`, and its duration at the end.

Saved replies and costs:

- Every LLM reply is saved in `results/cache/`, which is included in the repository. A rerun reuses a saved reply when the call is the same (same model, effort, prompt and call name): it costs nothing and gives the same answer, so only new calls, such as those for a changed or added task, go to the LLM.
- Add `--fresh` to any experiment or to `run_all.py` to ask the LLM again for every call (a new sample; the saved replies are overwritten). A full fresh run costs about $0.30 for Exp 1 and Exp 2 and $1.96 for Exp 3 (Opus), at list prices.
- A rerun moves the previous log to `results/logs/archive/` (not included in the repository), so each log describes one complete run.

Other options:

- `--tasks trunc_div3 pivot_index` runs only some tasks.
- `--results-dir <folder>` writes logs, cache, tables and figures to another folder instead of `results/`.
- Exp 3 takes `--model` and `--effort` to compare another writer; by default it uses `EXTRA_WRITER_MODEL` and `EXTRA_WRITER_THINKING_EFFORT` from `speccheck/config.py`. It only labels the specs (no attacks or repairs), and its log is kept apart from Exp 1, so it does not change the group results; the analysis compares the two writers in T10 and lists Exp 3 separately in T8 (cost) and T9 (Z3 unknowns).

All other settings (models, efforts, repeats, attack attempts, repair rounds, feedback types, Z3 timeout) are in `speccheck/config.py`.

### Troubleshooting

- `No API credentials`: set `ANTHROPIC_API_KEY` in the current terminal (step 5). The experiment scripts need it even when all replies are already saved.
- `401` or `authentication_error` from `check_api`: the key is missing, mistyped or revoked. An Anthropic API key starts with `sk-ant-`.
- `ModuleNotFoundError: No module named 'anthropic'` (or `z3`): the command used the system Python. Activate the environment (step 2) or use `.\.venv\Scripts\python.exe`.
- A traceback that ends in `KeyboardInterrupt` means the run was stopped with Ctrl+C, not that something failed.

## Code layout

All code is in `specattack/`:

| Path | Contents |
|---|---|
| `speccheck/` | the tool: tasks, loading of LLM code (ordinary Python, with static rules in `validate.py` and run-time guards in `loader.py`), Z3 checks, attacker, repair loop, LLM client with the reply cache, logging, and all settings in `config.py` |
| `speccheck/prompts/` | prompt templates for the writer, the repair and the attacker |
| `benchmarks/` | the 50 benchmark tasks in four groups (Group 4, in `group4_ai_generated.py`: 20 AI-generated very hard tasks) and their golden references, each with an AI-written second Z3 formula (`ai_z3_alternative`; `verify.py` checks that the two agree) |
| `fixtures/` | material that tests the tool, not part of the results: a few simple tasks and sample specs with known labels |
| `experiments/` | the runnable scripts: connection check, Exp 1, Exp 2, Exp 3 (shared options in `common.py`) |
| `analysis/` | tables T1, T2, T4 and T6 to T10, and charts F1 (specs fixed after each round) and F2 (fixed per round and per group, side by side) |
| `tests/` | unit tests |
| `results/` | logs, the reply cache, tables and figures of the runs reported in the final report |
| `run_all.py` | runs Exp 1, Exp 2, Exp 3 and the analysis in order |
