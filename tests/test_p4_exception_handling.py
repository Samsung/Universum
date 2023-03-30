# pylint: disable = redefined-outer-name

import os
import shutil
import pathlib
import pytest

from universum import __main__
from .conftest import FuzzyCallChecker
from .perforce_utils import P4TestEnvironment, PerforceWorkspace


@pytest.fixture()
def perforce_environment(perforce_workspace: PerforceWorkspace, tmp_path: pathlib.Path):
    yield P4TestEnvironment(perforce_workspace, tmp_path, test_type="main")


def test_p4_forbidden_local_revert(perforce_environment: P4TestEnvironment, stdout_checker: FuzzyCallChecker):
    p4 = perforce_environment.vcs_client.p4

    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Restrict changes", command=["chmod", "-R", "555", "."]),
                         dict(name="Check", command=["ls", "-la"])])
"""

    perforce_environment.shelve_config(config)
    result = __main__.run(perforce_environment.settings)
    # Clean up the directory at once to make sure it doesn't remain non-writable even if some assert fails
    os.system(f"chmod -R 777 {perforce_environment.temp_dir}")
    shutil.rmtree(str(perforce_environment.temp_dir))

    assert result == 0

    stdout_checker.assert_has_calls_with_param("[Errno 13] Permission denied")

    # make sure there are no pending CLs in the workspace
    assert not p4.run_changes("-c", perforce_environment.client_name, "-s", "pending")
    # make sure there are no pending changes in default CL
    assert not p4.run_opened("-C", perforce_environment.client_name)


def test_p4_print_exception_before_run(perforce_environment: P4TestEnvironment, stdout_checker: FuzzyCallChecker):
    p4 = perforce_environment.vcs_client.p4
    client = p4.fetch_client(perforce_environment.client_name)
    client["Options"] = "noallwrite noclobber nocompress locked nomodtime normdir"
    p4.save_client(client)

    settings = perforce_environment.settings
    result = __main__.run(settings)

    # Update client at once to make sure it doesn't remain locked even if some assert fails
    client = p4.fetch_client(perforce_environment.client_name)
    client["Options"] = "noallwrite noclobber nocompress unlocked nomodtime normdir"
    p4.save_client(client)

    assert result != 0
    stdout_checker.assert_has_calls_with_param(
        f"Errors during command execution( \"p4 client -d {perforce_environment.client_name}\" )")


def test_p4_print_exception_in_finalize(perforce_environment: P4TestEnvironment, stdout_checker: FuzzyCallChecker):
    p4 = perforce_environment.vcs_client.p4
    client = p4.fetch_client(perforce_environment.client_name)
    client["Options"] = "noallwrite noclobber nocompress locked nomodtime normdir"
    p4.save_client(client)

    settings = perforce_environment.settings
    settings.Main.finalize_only = True
    result = __main__.run(settings)

    # Update client at once to make sure it doesn't remain locked even if some assert fails
    client = p4.fetch_client(perforce_environment.client_name)
    client["Options"] = "noallwrite noclobber nocompress unlocked nomodtime normdir"
    p4.save_client(client)

    assert result == 0
    stdout_checker.assert_has_calls_with_param(
        f"Errors during command execution( \"p4 client -d {perforce_environment.client_name}\" )")
    stdout_checker.assert_has_calls_with_param("[Errno 2] No such file or directory")


@pytest.mark.parametrize('cl_list', [["132,456"], ["@123,@456"], ["//depot/...@,//depot2/...@"],
                                     ["//depot/...,//depot2/..."], ["132", "456"], ["@123", "4@456"],
                                     ["//depot/...@", "//depot2/...@"], ["//depot/...", "//depot2/..."]])
def test_p4_print_exception_in_sync(perforce_environment: P4TestEnvironment, stdout_checker: FuzzyCallChecker, cl_list):
    perforce_environment.settings.PerforceMainVcs.sync_cls = cl_list
    perforce_environment.run(expect_failure=True)
    text = f"Something went wrong when processing sync CL parameter ('{str(cl_list)}')"
    stdout_checker.assert_has_calls_with_param(text)


def test_p4_print_exception_wrong_shelve(perforce_environment: P4TestEnvironment, stdout_checker: FuzzyCallChecker):
    cl = perforce_environment.vcs_client.make_a_change()
    perforce_environment.settings.PerforceMainVcs.shelve_cls = [cl]

    # This is not the 'already committed' case of Swarm review, so it actually should fail
    perforce_environment.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param(
        f"Errors during command execution( \"p4 unshelve -s {cl} -f\" )")
    stdout_checker.assert_has_calls_with_param(f"[Error]: 'Change {cl} is already committed.'")
