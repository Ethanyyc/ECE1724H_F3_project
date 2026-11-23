"""The LLM attacker: hint, guess, check, retry."""

import time

from . import config, prompting
from .checks import check_program, check_realizable
from .feedback import REJECTED_REASON, attempt_failure, weak_sentence
from .loader import load_program
from .records import llm_fields
from .z3util import term_size


def attack(task, spec, spec_code, weak_example, llm, tag, context, attack_id, spec_id,
           attempts=config.ATTACK_ATTEMPTS):
    """Look for a wrong program that passes a too-weak spec. Returns an attack record.

    spec: the loaded spec; spec_code: its code as shown to the attacker;
    weak_example: the example of the single-output too-weak check.
    """
    start = time.perf_counter()
    hint = weak_sentence(task, weak_example)
    history = []
    log = []
    cost = {"tokens_in": 0, "tokens_out": 0, "tokens_thinking": 0, "cost_usd": 0.0, "latency_ms": 0.0}
    thinking_reported = True
    z3_time = 0.0
    record = {"attack_id": attack_id, "spec_id": spec_id, "task_id": task.id, "group": task.group,
              "has_array": task.has_array, "context": context, "hint": hint, "success": False,
              "program_code": None, "program_size": None, "source_size": None, "witness": None,
              "no_passing_program": None}

    for number in range(1, attempts + 1):
        prompt = prompting.attacker(task, spec_code, hint, history)
        result = llm.complete(prompt, tag=f"{tag}:attempt{number}")
        fields = llm_fields(result)
        for name in ("tokens_in", "tokens_out", "cost_usd", "latency_ms"):
            cost[name] += fields[name] or 0
        if fields["tokens_thinking"] is None:
            thinking_reported = False
        else:
            cost["tokens_thinking"] += fields["tokens_thinking"]
        program = load_program(result.text, task)
        entry = {"attempt": number, "program_code": program.code, "format_ok": program.ok,
                 "format_reason": program.reason or None, "passes_spec": None, "spec_cex": None,
                 "is_wrong": None, "rejected_reason": None, "model_version": fields["model_version"],
                 "cache_hit": fields["cache_hit"], "cache_key": fields["cache_key"],
                 "stop_reason": fields["stop_reason"]}
        if not program.ok:
            entry["rejected_reason"] = REJECTED_REASON["format"]
            history.append((program.code, attempt_failure("format", reason=program.reason)))
            log.append(entry)
            continue
        try:
            verdict = check_program(task, spec, program.term)
        except Exception as error:   # noqa: BLE001 - an odd program must not stop the experiment
            reason = f"error while checking the program: {type(error).__name__}: {error}"
            entry.update(format_ok=False, format_reason=reason, rejected_reason=REJECTED_REASON["format"])
            history.append((program.code, attempt_failure("format", reason=reason)))
            log.append(entry)
            continue
        z3_time += verdict["z3_time_ms"]
        entry["passes_spec"] = {"sat": False, "unsat": True}.get(verdict["passes_status"])
        entry["spec_cex"] = verdict.get("cex")
        if "wrong_status" in verdict:
            entry["is_wrong"] = {"sat": True, "unsat": False}.get(verdict["wrong_status"])
        if verdict["verdict"] == "success":
            log.append(entry)
            record.update(success=True, program_code=program.code, program_size=term_size(program.term),
                          source_size=program.source_size, witness=verdict["witness"])
            break
        entry["rejected_reason"] = REJECTED_REASON[verdict["verdict"]]
        history.append((program.code, attempt_failure(verdict["verdict"], cex=verdict.get("cex"))))
        log.append(entry)

    if not record["success"]:
        realizable = check_realizable(task, spec)
        z3_time += realizable["time_ms"]
        record["no_passing_program"] = realizable["status"]

    record.update(attempts=log, attempts_used=len(log), z3_time_ms=round(z3_time, 3),
                  tokens_in=cost["tokens_in"], tokens_out=cost["tokens_out"],
                  tokens_thinking=cost["tokens_thinking"] if thinking_reported else None,
                  cost_usd=round(cost["cost_usd"], 6), llm_latency_ms=round(cost["latency_ms"], 1),
                  wall_time_ms=round((time.perf_counter() - start) * 1000, 1))
    return record
