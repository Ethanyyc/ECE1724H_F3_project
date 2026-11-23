You are writing a formal specification of a function, as a precondition and a postcondition in Python with the Z3 library.

Task: $description

Inputs: $inputs
The function's result is called r (an integer).

Write two Python functions:
- pre($params) returns a Z3 Boolean formula that holds exactly for the inputs the function may be called with.
- post($params, r) returns a Z3 Boolean formula that holds exactly when r is a correct result for those inputs.

$language

Example for a different task ("Return x if x is positive, otherwise 0."; input x: integer):

```python
def pre(x):
    return True

def post(x, r):
    return And(r >= 0, r >= x, Or(r == 0, r == x))
```

Reply with exactly one Python code block that defines pre and post.
