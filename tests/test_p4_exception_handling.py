# pylint: disable = redefined-outer-name

import pytest
import sh

from universum import __main__
from .perforce_utils import P4TestEnvironment
from .utils import simple_test_config


@pytest.fixture()
def perforce_environment(perforce_workspace, tmpdir):
    yield P4TestEnvironment(perforce_workspace, tmpdir, test_type="main")


def test_p4_forbidden_local_revert(perforce_environment, stdout_checker):
    p4 = perforce_environment.vcs_client.p4

    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Restrict changes", command=["chmod", "-R", "555", "."]),
                         dict(name="Check", command=["ls", "-la"])])
"""

    perforce_environment.shelve_config(config)
    result = __main__.run(perforce_environment.settings)
    # Clean up the directory at once to make sure it doesn't remain non-writable even if some assert fails
    perforce_environment.temp_dir.chmod(0o0777, rec=1)
    perforce_environment.temp_dir.remove(rec=1)

    assert result == 0

    stdout_checker.assert_has_calls_with_param("[Errno 13] Permission denied")

    # make sure there are no pending CLs in the workspace
    assert not p4.run_changes("-c", perforce_environment.client_name, "-s", "pending")
    # make sure there are no pending changes in default CL
    assert not p4.run_opened("-C", perforce_environment.client_name)


def test_p4_print_exception_before_run(perforce_environment, stdout_checker):
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


def test_p4_print_exception_in_finalize(perforce_environment, stdout_checker):
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
def test_p4_print_exception_in_sync(perforce_environment, stdout_checker, cl_list):
    perforce_environment.settings.PerforceMainVcs.sync_cls = cl_list
    perforce_environment.run(expect_failure=True)
    text = f"Something went wrong when processing sync CL parameter ('{str(cl_list)}')"
    stdout_checker.assert_has_calls_with_param(text)


def test_p4_print_exception_wrong_shelve(perforce_environment, stdout_checker):
    cl = perforce_environment.vcs_client.make_a_change()
    perforce_environment.settings.PerforceMainVcs.shelve_cls = [cl]

    # This is not the 'already committed' case of Swarm review, so it actually should fail
    perforce_environment.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param(
        f"Errors during command execution( \"p4 unshelve -s {cl} -f\" )")
    stdout_checker.assert_has_calls_with_param(f"[Error]: 'Change {cl} is already committed.'")


@pytest.fixture()
def mock_diff(monkeypatch):
    def mocking_function(*args, **kwargs):
        raise sh.ErrorReturnCode(stderr=b"This is error text\n F\xc3\xb8\xc3\xb6\xbbB\xc3\xa5r",
                                 stdout=b"This is text'",
                                 full_cmd="any shell call with any params")

    monkeypatch.setattr(sh, 'Command', mocking_function, raising=False)


def test_p4_diff_exception_handling(perforce_environment, mock_diff, stdout_checker):
    perforce_environment.shelve_config(simple_test_config)
    perforce_environment.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("This is error text")
    # Without the fixes all error messages go to stderr instead of stdout
