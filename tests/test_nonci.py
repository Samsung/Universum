#!/usr/bin/env python
# -*- coding: UTF-8 -*-


config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="test_step", artifacts="test_nonci.txt",
                           command=["bash", "-c", '''echo "test nonci" > test_nonci.txt'''])])
"""


def test_launcher_output(universum_runner_nonci):
    artifact_dir = universum_runner_nonci.artifact_dir
    file_output_expected = "Adding file " + artifact_dir + "/test_step_log.txt to artifacts"
    step_log_expected = """/bin/bash -c echo "test nonci" > test_nonci.txt"""
    ad_param = '-ad ' + artifact_dir

    console_out_log = universum_runner_nonci.run(config, additional_parameters=ad_param) # defult -lo is console
    assert file_output_expected not in console_out_log
    assert step_log_expected in console_out_log
    # nonci doesn't required to clean artifacts between calls

    log = universum_runner_nonci.run(config, additional_parameters='-lo file ' + ad_param)
    assert file_output_expected in log
    assert step_log_expected in console_out_log

    assert console_out_log != log
    step_log = universum_runner_nonci.environment.assert_successful_execution(
        'cat ' + artifact_dir + "/test_step_log.txt")
    assert step_log_expected in step_log


    # second call of universum must contain only latest step log
    log = universum_runner_nonci.run(config, additional_parameters='-lo file ' + ad_param)
    assert file_output_expected in log
    assert step_log_expected in log

    second_run_step_log = universum_runner_nonci.environment.assert_successful_execution(
        'cat ' + artifact_dir + "/test_step_log.txt")
    assert step_log == second_run_step_log
