#!/usr/bin/env python
# -*- coding: UTF-8 -*-


from __future__ import absolute_import

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
        ["step :!step 1", ["parent 1", "parent 2", "step 2"], ["step 1"]],

        ["", ["parent 1", "parent 2", "parent 1 step 1", "parent 2 step 1", "parent 1 step 2", "parent 2 step 2"], []],
        ["!", ["parent 1", "parent 2", "parent 1 step 1", "parent 2 step 1", "parent 1 step 2", "parent 2 step 2"],
         []],))
def test_steps_filter(docker_main_and_nonci, filters, expected_logs, unexpected_logs):
    console_out_log = docker_main_and_nonci.run(config, additional_parameters="-o console -f='{}'".format(filters))
    for log_str in expected_logs:
        assert log_str in console_out_log

    for log_str in unexpected_logs:
        assert log_str not in console_out_log


def test_steps_filter_few_flags(docker_main_and_nonci):
    console_out_log = docker_main_and_nonci.run(config,
                                                additional_parameters="-o console -f='parent 1:parent 2' -f='!step 1'")
    for log_str in ["parent 1", "step 2", "parent 2"]:
        assert log_str in console_out_log

    assert "step 1" not in console_out_log
