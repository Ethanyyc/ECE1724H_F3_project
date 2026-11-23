"""Readable sentences for check results, attacker hints and repair feedback."""

from .checks import CHECKS


def format_inputs(values):
    return ", ".join(f"{name} = {value}" for name, value in values.items())


def describe_problem(task, check, example):
    """One sentence for a failed check."""
    if check == "empty":
        return "No allowed input satisfies your precondition, so your spec allows no input at all."
    inputs = format_inputs(example["inputs"])
    if check == "strict":
        return f"Your precondition rules out the input {inputs}, which is an allowed input."
    if check == "strong":
        kind = "the intended output" if task.one_answer else "an acceptable output"
        return f"For the input {inputs}, your spec rejects the output {example['output']}, which is {kind}."
    if check == "weak":
        return weak_sentence(task, example)
    raise ValueError(check)


def weak_sentence(task, example):
    inputs = format_inputs(example["inputs"])
    if task.one_answer:
        return (f"For the input {inputs}, your spec accepts the output {example['output']}, "
                f"but the intended output is {example['intended']}.")
    sentence = f"For the input {inputs}, your spec accepts the output {example['output']}, which is not acceptable"
    if example.get("acceptable") is not None:
        sentence += f"; {example['acceptable']} would be acceptable"
    return sentence + "."


def failed_checks(check_result):
    return [name for name in CHECKS if check_result["checks"][name]["problem"] is True]


def describe(task, check_result, feedback_type, attack=None):
    """Feedback text for a spec with at least one failed check.

    feedback_type 1: pass/fail only; 2: one example per failed check;
    3: as 2, but the too-weak problem is reported with the attacker's program.
    `attack` is the attack record for type 3 (success flag and program code).
    Returns (text, fell_back_to_example).
    """
    failed = failed_checks(check_result)
    if not failed:
        raise ValueError("describe() needs a spec with a failed check")
    if feedback_type == 1:
        return "Your spec is wrong.", False
    lines = []
    fell_back = False
    for name in failed:
        example = check_result["checks"][name]["example"]
        if name == "weak" and feedback_type == 3:
            if attack is not None and attack.get("success"):
                lines.append("Your spec accepts this wrong implementation:\n```python\n"
                             f"{attack['program_code'].strip()}\n```")
                continue
            fell_back = True
        lines.append(describe_problem(task, name, example))
    return "\n".join(lines), fell_back


def format_error(previous_feedback, reason):
    note = (f"Your previous reply did not follow the required format: {reason}. "
            "Reply with exactly one Python code block that defines pre and post.")
    return f"{previous_feedback}\n{note}" if previous_feedback else note


def attempt_failure(verdict, reason=None, cex=None):
    """Why an attacker attempt was rejected, as told to the attacker."""
    if verdict == "format":
        return f"Your reply did not follow the required format: {reason}."
    if verdict == "fails_spec":
        return (f"Your program does not pass the spec: for the input {format_inputs(cex['inputs'])}, "
                f"it returns {cex['output']}, which the spec rejects.")
    if verdict == "correct":
        return ("Your program is actually correct on every allowed input. It must be wrong on at least one "
                "allowed input that satisfies the precondition, while still passing the spec.")
    if verdict == "undetermined":
        return "Z3 could not decide whether your program passes the spec within the time limit. Try a simpler program."
    raise ValueError(verdict)


REJECTED_REASON = {
    "format": "did not follow the format",
    "fails_spec": "did not pass the spec",
    "correct": "was actually correct",
    "undetermined": "Z3 undetermined",
}
