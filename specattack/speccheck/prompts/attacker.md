You are testing a formal specification by looking for a wrong implementation that the specification still accepts.

Task: $description

Inputs: $inputs

Specification (Python with Z3; pre is the precondition, post the postcondition, r the result):

```python
$spec_code
```

This specification is too weak. Hint: $hint

Write the simplest plausible implementation of the task that passes this specification on every input that satisfies pre, but is wrong: on at least one input that satisfies pre, it must return a result that is not correct for the task.

Write it as a Python function prog($params) that returns a Z3 integer expression. For yes/no results, return If(condition, 1, 0).

$language
$history
Reply with exactly one Python code block that defines prog.
