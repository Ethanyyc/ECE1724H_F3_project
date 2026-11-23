"""Hand-written material that tests the tool itself; none of it is part of the
experiments' results; the unit tests use it.

- simple_tasks: small tasks (min2, clamp, count_eq, ...) used by the tests and
  the sample specs. benchmarks.get() also finds them by id.
- sample_specs: specs and programs with known labels, and code the loader must
  accept or reject.
"""

from .simple_tasks import TASKS

__all__ = ["TASKS"]
