"""Registry of the 50 benchmark tasks in four groups: integer functions, array
problems, tasks with many correct answers, and AI-generated very hard tasks.

get() also finds the simple fixture tasks (fixtures/), which the unit tests use;
select() returns benchmark tasks only.
"""

from fixtures import TASKS as FIXTURE_TASKS

from . import group1_integer, group2_array, group3_many_answer, group4_ai_generated

ALL_TASKS = group1_integer.TASKS + group2_array.TASKS + group3_many_answer.TASKS + group4_ai_generated.TASKS
BY_ID = {task.id: task for task in ALL_TASKS}
FIXTURES_BY_ID = {task.id: task for task in FIXTURE_TASKS}

if len(BY_ID) != len(ALL_TASKS) or len(FIXTURES_BY_ID) != len(FIXTURE_TASKS):
    raise ValueError("duplicate task ids")
if set(BY_ID) & set(FIXTURES_BY_ID):
    raise ValueError("a benchmark task and a fixture share an id")


def get(task_id):
    """A benchmark task, or a fixture task."""
    if task_id in BY_ID:
        return BY_ID[task_id]
    return FIXTURES_BY_ID[task_id]


def select(task_ids=None):
    """All benchmark tasks, or the named ones in registry order."""
    if not task_ids:
        return list(ALL_TASKS)
    unknown = [t for t in task_ids if t not in BY_ID]
    if unknown:
        raise KeyError(f"unknown benchmark task id(s): {', '.join(unknown)}")
    wanted = set(task_ids)
    return [task for task in ALL_TASKS if task.id in wanted]
