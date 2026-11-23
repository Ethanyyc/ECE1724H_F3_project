import z3

import benchmarks
from speccheck.tasks import INPUT_PREFIX
from speccheck.z3util import concrete_int, truth


def test_registry_has_50_tasks_in_four_groups():
    assert len(benchmarks.ALL_TASKS) == 50
    sizes = {group: sum(1 for t in benchmarks.ALL_TASKS if t.group == group) for group in (1, 2, 3, 4)}
    assert sizes == {1: 10, 2: 10, 3: 10, 4: 20}


def test_groups_1_and_2_have_one_answer_and_group_3_many():
    for task in benchmarks.ALL_TASKS:
        if task.group in (1, 2, 3):
            assert task.one_answer == (task.group in (1, 2)), task.id
    assert all(t.one_answer for t in benchmarks.ALL_TASKS if t.group == 4)


def test_every_task_has_hand_picked_cases():
    for task in benchmarks.ALL_TASKS:
        assert len(task.cases) >= 3, task.id


def test_golden_cases_hold():
    for task in benchmarks.ALL_TASKS:
        for case in task.cases:
            if task.one_answer:
                values, expected = case
                assert concrete_int(task.golden_program(*task.concrete(values))) == expected, (task.id, values)
            else:
                values, output, accepted = case
                assert truth(task.golden_spec(*task.concrete(values), z3.IntVal(output))) == accepted, (task.id, case)


def test_inputs_use_reserved_names():
    for task in benchmarks.ALL_TASKS:
        for term in task.inputs():
            assert term.decl().name().startswith(INPUT_PREFIX)


def test_select_keeps_registry_order_and_rejects_unknown_ids():
    assert [t.id for t in benchmarks.select(["median_of_four", "trunc_div3"])] == ["trunc_div3", "median_of_four"]
    for bad in (["nope"], ["clamp"]):        # fixtures are not benchmark tasks
        try:
            benchmarks.select(bad)
        except KeyError:
            continue
        raise AssertionError(f"expected KeyError for {bad}")


def test_fixtures_are_reachable_by_id_and_their_cases_hold():
    assert benchmarks.get("clamp").id == "clamp"
    for task in benchmarks.FIXTURE_TASKS:
        for case in task.cases:
            if task.one_answer:
                values, expected = case
                assert concrete_int(task.golden_program(*task.concrete(values))) == expected, (task.id, values)
            else:
                values, output, accepted = case
                assert truth(task.golden_spec(*task.concrete(values), z3.IntVal(output))) == accepted, (task.id, case)
