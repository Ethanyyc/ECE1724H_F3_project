"""The repair loop.

Each round is one rewrite by the spec writer followed by a full check, so the
spec produced by the last round is always checked. An invalid reply uses up
its round; the last valid spec is kept and the next prompt adds the format
error to the previous feedback.
"""

import time

from . import config, prompting
from .attacker import attack
from .checks import CORRECT, FORMAT_FAILURE, TOO_WEAK, UNDETERMINED, try_check_spec
from .feedback import describe, format_error
from .loader import LoadedSpec, load_spec
from .records import spec_record


def run_repair(task, start, feedback_type, writer, attacker_llm, logger, start_attack=None,
               rounds=config.REPAIR_ROUNDS):
    """Repair one too-weak first spec with one feedback type. Returns the repair record.

    start: the Exp 1 spec record of the starting spec (its code and check results).
    start_attack: the Exp 1 attack record on the starting spec, reused in round 1 of type 3.
    Revised specs and attacks run inside the loop are written to the logger as they happen.
    """
    started = time.perf_counter()
    spec_id = start["spec_id"]
    repair_id = f"{spec_id}:t{feedback_type}"
    spec = load_spec(start["code"], task, is_reply=False)
    if not spec.ok:
        raise ValueError(f"starting spec {spec_id} does not load: {spec.reason}")
    current = {"code": start["code"], "check": {"checks": start["checks"], "labels": start["labels"]}}
    if TOO_WEAK not in start["labels"]:
        raise ValueError(f"starting spec {spec_id} is not too weak")

    totals = {"cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0, "tokens_thinking": 0, "z3_time_ms": 0.0}
    thinking_reported = True

    def add_cost(source):
        nonlocal thinking_reported
        for name in ("cost_usd", "tokens_in", "tokens_out", "z3_time_ms"):
            totals[name] += source.get(name) or 0
        if source.get("tokens_thinking") is None:
            thinking_reported = False
        else:
            totals["tokens_thinking"] += source["tokens_thinking"]

    def attack_current(round_number, spec_obj, code, check, current_spec_id):
        if start_attack is not None and round_number == 1:
            return start_attack
        weak_example = check["checks"]["weak"]["example"]
        record = attack(task, spec_obj, code, weak_example, attacker_llm,
                        tag=f"exp2:{repair_id}:k{round_number}:attack",
                        context=f"repair_t{feedback_type}_round_{round_number}",
                        attack_id=f"{current_spec_id}:attack:t{feedback_type}:k{round_number}",
                        spec_id=current_spec_id)
        logger.write("attack", record)
        add_cost(record)
        return record

    def feedback_for(round_number, spec_obj, code, check, current_spec_id):
        attack_record = None
        if feedback_type == 3 and TOO_WEAK in check["labels"]:
            attack_record = attack_current(round_number, spec_obj, code, check, current_spec_id)
        text, fell_back = describe(task, check, feedback_type, attack_record)
        attack_id = attack_record["attack_id"] if attack_record else None
        return text, fell_back, attack_id

    feedback, fell_back, attack_id = feedback_for(1, spec, current["code"], current["check"], spec_id)
    round_log = []
    outcome, rounds_to_correct = "incorrect", None
    current_spec_id = spec_id

    for k in range(1, rounds + 1):
        prompt = prompting.repair(task, current["code"], feedback)
        result = writer.complete(prompt, tag=f"exp2:{repair_id}:k{k}")
        loaded = load_spec(result.text, task)
        check = None
        if loaded.ok:
            check, error = try_check_spec(task, loaded)
            if error:
                loaded = LoadedSpec(False, error, loaded.code, loaded.pre_code, loaded.post_code)
        entry = {"k": k, "feedback_text": feedback, "attack_id": attack_id, "fell_back_to_example": fell_back,
                 "reply_format_ok": loaded.ok, "format_reason": loaded.reason or None, "spec_id": None,
                 "labels": None}
        new_id = f"{repair_id}:k{k}"
        if not loaded.ok:
            logger.write("spec", spec_record(new_id, task, "revised", start["repeat"], current_spec_id,
                                             result, loaded, None,
                                             extra={"feedback_type": feedback_type, "round": k}))
            add_cost({"cost_usd": result.cost_usd, "tokens_in": result.tokens_in,
                      "tokens_out": result.tokens_out, "tokens_thinking": result.tokens_thinking})
            entry["spec_id"] = new_id
            entry["labels"] = [FORMAT_FAILURE]
            round_log.append(entry)
            # The next prompt repeats this feedback, so attack_id and fell_back still describe it.
            feedback = format_error(feedback, loaded.reason)
            continue
        logger.write("spec", spec_record(new_id, task, "revised", start["repeat"], current_spec_id, result,
                                         loaded, check, extra={"feedback_type": feedback_type, "round": k}))
        add_cost({"cost_usd": result.cost_usd, "tokens_in": result.tokens_in, "tokens_out": result.tokens_out,
                  "tokens_thinking": result.tokens_thinking, "z3_time_ms": check["z3_time_ms"]})
        entry["spec_id"] = new_id
        entry["labels"] = check["labels"]
        round_log.append(entry)
        spec, current_spec_id = loaded, new_id
        current = {"code": loaded.code, "check": check}
        if check["labels"] == [CORRECT]:
            outcome, rounds_to_correct = "correct", k
            break
        if check["labels"] == [UNDETERMINED]:
            outcome = "undetermined"
            break
        if k < rounds:
            feedback, fell_back, attack_id = feedback_for(k + 1, spec, current["code"], check, current_spec_id)

    return {
        "repair_id": repair_id,
        "start_spec_id": spec_id,
        "task_id": task.id,
        "group": task.group,
        "has_array": task.has_array,
        "feedback_type": feedback_type,
        "start_labels": start["labels"],
        "rounds": round_log,
        "rounds_used": len(round_log),
        "outcome": outcome,
        "rounds_to_correct": rounds_to_correct,
        "final_spec_id": current_spec_id,
        "final_labels": current["check"]["labels"],
        "cost_usd": round(totals["cost_usd"], 6),
        "tokens_in": totals["tokens_in"],
        "tokens_out": totals["tokens_out"],
        "tokens_thinking": totals["tokens_thinking"] if thinking_reported else None,
        "z3_time_ms": round(totals["z3_time_ms"], 3),
        "wall_time_ms": round((time.perf_counter() - started) * 1000, 1),
    }
