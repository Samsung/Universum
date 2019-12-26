#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import pytest


config = """
from _universum.configuration_support import Variations

def step(name, cmd=False):
    return Variations([dict(name=name, command=[] if not cmd else ["bash", "-c", '''echo "run step"'''])])

configs = step('parent 1 ') * (step('step 1', True) + step('step 2', True))
configs += step('parent 2 ') * (step('step 1', True) + step('step 2', True))
"""

@pytest.mark.parametrize("filters,expected_logs, unexpected_logs", (
    ["parent 1", ["parent 1", "step 1", "step 2"], ["parent 2"]],
    ["!parent 2", ["parent 1", "step 1", "step 2"], ["parent 2"]],
    ["parent 1:parent 2", ["parent 1", "step 1", "step 2", "parent 2"], []],

    ["parent 1:parent 2:!step 1", ["parent 1", "step 2", "parent 2"], ["step 1"]],
    ["step 2", ["parent 1", "parent 2", "step 2"], ["step 1"]],
    ["!step 2:parent 1", ["parent 1", "step 1"], ["parent 2", "step 2"]],
    ["step :!step 1", ["parent 1", "parent 2", "step 2"], ["step 1"]], ))
@pytest.mark.nonci_applicable
def test_run_step_filter(universum_runner, filters, expected_logs, unexpected_logs):
    console_out_log = universum_runner.run(config, additional_parameters="-lo console --run-step='{}'".format(filters))
    for log_str in expected_logs:
        assert log_str in console_out_log

    for log_str in unexpected_logs:
        assert log_str not in console_out_log
