#!/usr/bin/env python
# -*- coding: UTF-8 -*-


config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="test_step", artifacts="test_nonci.txt",
                           command=["bash", "-c", '''echo "test nonci" > test_nonci.txt'''])])
"""


def test_launcher_output(universum_runner_nonci):
    file_output_expected = "Adding file /artifacts/test_step_log.txt to artifacts"

    console_out_log = universum_runner_nonci.run(config) # defult -lo is console
    assert file_output_expected not in console_out_log
    # nonci doesn't required to clean artifacts between calls

    log = universum_runner_nonci.run(config, additional_parameters='-lo file')
    assert file_output_expected in log, log
    assert console_out_log != log

