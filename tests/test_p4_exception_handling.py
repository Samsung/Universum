# pylint: disable = redefined-outer-name

import pytest

from universum import __main__
from .perforce_utils import P4Environment


@pytest.fixture()
def perforce_environment(perforce_workspace, tmpdir):
    yield P4Environment(perforce_workspace, tmpdir, test_type="main")


def test_p4_forbidden_local_revert(perforce_environment, stdout_checker):
    p4 = perforce_environment.p4
    p4_file = perforce_environment.repo_file

    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Restrict changes", command=["chmod", "-R", "555", "."]),
                         dict(name="Check", command=["ls", "-la"])])
"""
    p4.run_edit(perforce_environment.depot)
    p4_file.write(config)
    change = p4.fetch_change()
    change["Description"] = "CL for shelving"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    settings = perforce_environment.settings
    settings.PerforceMainVcs.shelve_cls = [shelve_cl]
    settings.Launcher.config_path = p4_file.basename

    result = __main__.run(settings)
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
    p4 = perforce_environment.p4
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
        "Errors during command execution( \"p4 client -d {}\" )".format(perforce_environment.client_name))


def test_p4_print_exception_in_finalize(perforce_environment, stdout_checker):
    p4 = perforce_environment.p4
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
        "Errors during command execution( \"p4 client -d {}\" )".format(perforce_environment.client_name))
    stdout_checker.assert_has_calls_with_param("[Errno 2] No such file or directory")


@pytest.mark.parametrize('cl_list', [["132,456"], ["@123,@456"], ["//depot/...@,//depot2/...@"],
                                     ["//depot/...,//depot2/..."], ["132", "456"], ["@123", "4@456"],
                                     ["//depot/...@", "//depot2/...@"], ["//depot/...", "//depot2/..."]])
def test_p4_print_exception_in_sync(perforce_environment, stdout_checker, cl_list):
    settings = perforce_environment.settings
    settings.PerforceMainVcs.sync_cls = cl_list
    result = __main__.run(settings)

    assert result == 1
    text = f"Something went wrong when processing sync CL parameter ('{str(cl_list)}')"
    stdout_checker.assert_has_calls_with_param(text)


def test_p4_print_exception_wrong_shelve(perforce_environment, stdout_checker):
    cl = perforce_environment.make_a_change()

    settings = perforce_environment.settings
    settings.PerforceMainVcs.shelve_cls = [cl]
    result = __main__.run(settings)

    # This is not the 'already committed' case of Swarm review, so it actually should fail
    assert result == 1
    stdout_checker.assert_has_calls_with_param(
        "Errors during command execution( \"p4 unshelve -s {} -f\" )".format(cl))
    stdout_checker.assert_has_calls_with_param(f"[Error]: 'Change {cl} is already committed.'")
