"""Settings for every experiment. Change values here, not in the code."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_DIR = ROOT / "results"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Tasks
N = 4                                   # length of every fixed-length array

# Z3
Z3_TIMEOUT_MS = 30_000                  # per query
Z3_SEED = 0
SMALL_MODEL_BOUND = 20                  # examples are first searched with all values in [-20, 20]
SMALL_MODEL_TIMEOUT_MS = 2_000

# Experiments
REPEATS = 3                             # first specs per task (Exp 1)
ATTACK_ATTEMPTS = 3
REPAIR_ROUNDS = 3
# Repair feedback types (Exp 2):
# - 1: pass/fail only ("Your spec is wrong.")
# - 2: one concrete example per failed check (an input and the output the spec
#      wrongly accepts or rejects)
# - 3: as 2, but the too-weak problem is shown as the attacker's wrong program
#      that the spec accepts
FEEDBACK_TYPES = (1, 2, 3)

# LLMs: Anthropic model ids, called through the Anthropic API. All use
# adaptive thinking (thinking={"type": "adaptive"}, output_config={"effort":
# ...}); with thinking on, the API does not accept a custom temperature. The
# model that actually answered is logged as model_version.
WRITER_MODEL = "claude-haiku-5-5"       # Claude Haiku 5.5 writes and repairs specs
ATTACKER_MODEL = "claude-sonnet-5-5"    # Claude Sonnet 5.5 attacks
WRITER_THINKING_EFFORT = "medium"       # "low", "medium", "high", "xhigh" or "max"
ATTACKER_THINKING_EFFORT = "medium"
MAX_TOKENS = 16_000                     # thinking and answer together

# Exp 3 (extension of RQ1): the same first specs from a more capable writer, at
# the default writer's effort so that only the model differs.
EXTRA_WRITER_MODEL = "claude-opus-5-5"   # --model overrides it
EXTRA_WRITER_THINKING_EFFORT = "medium"
LLM_TIMEOUT_S = 600
LLM_MAX_RETRIES = 5

# USD per million tokens (Anthropic price list, November 2026); output includes
# thinking tokens.
PRICES_PER_MTOK = {
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00},
    "claude-opus-5-5": {"input": 4.00, "output": 20.00},
}
