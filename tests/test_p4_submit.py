#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import copy
import pytest

import universum

from . import perforce_utils, utils


@pytest.fixture()
def p4_submit_environment(perforce_workspace, tmpdir):
    yield perforce_utils.P4Environment(perforce_workspace, tmpdir, test_type="submit")


def test_fail_changing_non_checked_out_file(p4_submit_environment):
    target_file = p4_submit_environment.nonwritable_file
    text = utils.randomize_name("This is change ")
    with pytest.raises(IOError) as excinfo:
        with open(str(target_file), "w") as tmpfile:
            tmpfile.write(text + "\n")

    assert "Permission denied" in unicode(excinfo.value)


def test_success_changing_checked_out_file(p4_submit_environment):
    target_file = p4_submit_environment.nonwritable_file

    p4_submit_environment.p4.run("edit", str(target_file))

    text = utils.randomize_name("This is change ")
    target_file.write(text + "\n")

    change = p4_submit_environment.p4.run_change("-o")[0]
    change["Description"] = "Test submit"
    p4_submit_environment.p4.run_submit(change)

    assert p4_submit_environment.file_present(str(target_file))


@pytest.mark.parametrize("test_type,expected",
                         [("open", 0), ("write", 1), ("review", 1)],
                         ids=["open", "write", "review"])
def test_fail_protected_branch(p4_submit_environment, test_type, expected):
    protected_dir = p4_submit_environment.vcs_cooking_dir.mkdir(test_type + "-protected")
    file_to_add = protected_dir.join("new_file.txt")
    text = "This is a new line in the file"
    file_to_add.write(text + "\n")

    settings = copy.deepcopy(p4_submit_environment.settings)
    setattr(settings.Submit, "reconcile_list", [unicode(file_to_add)])

    result = universum.run(settings)
    assert result == expected

    p4 = p4_submit_environment.p4
    assert not p4.run_changes("-c", p4_submit_environment.client_name, "-s", "pending")
    assert not p4.run_opened("-C", p4_submit_environment.client_name)
