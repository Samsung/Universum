# pylint: disable = redefined-outer-name

import pathlib
import pytest

from . import utils
from .perforce_utils import P4TestEnvironment, PerforceWorkspace


@pytest.fixture()
def p4_submit_environment(perforce_workspace: PerforceWorkspace, tmp_path: pathlib.Path):
    yield P4TestEnvironment(perforce_workspace, tmp_path, test_type="submit")


def test_fail_changing_non_checked_out_file(p4_submit_environment: P4TestEnvironment):
    target_file = p4_submit_environment.vcs_client.nonwritable_file
    text = utils.randomize_name("This is change ")
    with pytest.raises(IOError) as excinfo:
        with open(str(target_file), "w", encoding="utf-8") as tmpfile:
            tmpfile.write(text + "\n")

    assert "Permission denied" in str(excinfo.value)


def test_success_changing_checked_out_file(p4_submit_environment: P4TestEnvironment):
    target_file = p4_submit_environment.vcs_client.nonwritable_file

    p4_submit_environment.vcs_client.p4.run("edit", str(target_file))

    text = utils.randomize_name("This is change ")
    target_file.write_text(text + "\n")

    change = p4_submit_environment.vcs_client.p4.run_change("-o")[0]
    change["Description"] = "Test submit"
    p4_submit_environment.vcs_client.p4.run_submit(change)

    assert p4_submit_environment.vcs_client.file_present(str(target_file))
