# pylint: disable = redefined-outer-name

import pytest

from . import perforce_utils, utils


@pytest.fixture()
def p4_submit_environment(perforce_workspace, tmpdir):
    yield perforce_utils.P4Environment(perforce_workspace, tmpdir, test_type="submit")


def test_fail_changing_non_checked_out_file(p4_submit_environment):
    target_file = p4_submit_environment.nonwritable_file
    text = utils.randomize_name("This is change ")
    with pytest.raises(IOError) as excinfo:
        with open(str(target_file), "w", encoding="utf-8") as tmpfile:
            tmpfile.write(text + "\n")

    assert "Permission denied" in str(excinfo.value)


def test_success_changing_checked_out_file(p4_submit_environment):
    target_file = p4_submit_environment.nonwritable_file

    p4_submit_environment.p4.run("edit", str(target_file))

    text = utils.randomize_name("This is change ")
    target_file.write(text + "\n")

    change = p4_submit_environment.p4.run_change("-o")[0]
    change["Description"] = "Test submit"
    p4_submit_environment.p4.run_submit(change)

    assert p4_submit_environment.file_present(str(target_file))
