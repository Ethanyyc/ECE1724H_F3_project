"""Builders for the log records."""

from .checks import FORMAT_FAILURE


def llm_fields(result):
    if result is None:
        return {"model": None, "model_version": None, "tokens_in": 0, "tokens_out": 0, "tokens_thinking": None,
                "cost_usd": 0.0, "latency_ms": 0.0, "cache_hit": None, "cache_key": None, "stop_reason": None,
                "thinking": None}
    return {"model": result.model, "model_version": result.model_version, "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out, "tokens_thinking": result.tokens_thinking,
            "cost_usd": result.cost_usd, "latency_ms": result.latency_ms, "cache_hit": result.cache_hit,
            "cache_key": result.cache_key, "stop_reason": result.stop_reason, "thinking": result.thinking}


def spec_record(spec_id, task, source, repeat, parent_spec_id, llm_result, loaded, check_result, extra=None):
    """One spec: golden, first or revised. check_result is None if the format check failed."""
    record = {
        "spec_id": spec_id,
        "task_id": task.id,
        "group": task.group,
        "has_array": task.has_array,
        "one_answer": task.one_answer,
        "source": source,
        "repeat": repeat,
        "parent_spec_id": parent_spec_id,
        "raw_reply": llm_result.text if llm_result is not None else None,
        "code": loaded.code,
        "pre_code": loaded.pre_code,
        "post_code": loaded.post_code,
        "format_ok": loaded.ok,
        "format_reason": loaded.reason or None,
    }
    if check_result is None:
        record.update(checks=None, equivalence=None, labels=[FORMAT_FAILURE], cross_check_ok=None,
                      z3_time_ms=0.0)
    else:
        record.update(checks=check_result["checks"], equivalence=check_result["equivalence"],
                      labels=check_result["labels"], cross_check_ok=check_result["cross_check_ok"],
                      z3_time_ms=check_result["z3_time_ms"])
    record.update(llm_fields(llm_result))
    record.update(extra or {})
    return record
