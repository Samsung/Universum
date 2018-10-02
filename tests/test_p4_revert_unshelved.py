# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import os
import pytest

from _universum.lib.gravity import construct_component
from _universum.modules.vcs import perforce_vcs, vcs
from . import utils


class DiffParameters(object):
    def __init__(self, environment):
        self.env = environment

        for env_var in ["P4_PATH", "P4_MAPPINGS"]:
            try:
                del os.environ[env_var]
            except KeyError:
                pass

        settings = utils.create_settings(vcs.MainVcs)
        settings.PerforceVcs.port = environment.p4.port
        settings.PerforceVcs.user = environment.p4.user
        settings.PerforceVcs.password = environment.p4.password
        settings.Output.type = "term"
        settings.ProjectDirectory.project_root = str(self.env.root_directory + "/../new_workspace")
        settings.PerforceWithMappings.mappings = [self.env.depot + " /..."]
        settings.PerforceMainVcs.force_clean = True
        settings.PerforceMainVcs.client = "new_client"

        self.perforce = construct_component(perforce_vcs.PerforceMainVcs, settings)

        self.perforce.connect()
        self.perforce.create_workspace()

    def run_diff(self, shelve):
        if not self.perforce.p4.run_opened():
            self.perforce.shelve_cls = [shelve["change"]]
            self.perforce.unshelve()
            files_to_compare = self.perforce.copy_cl_files_and_revert()
            is_opened = self.perforce.p4.run_opened()
            return files_to_compare, is_opened
        return None, "There is some opened files in new_workspace. Please, revert them before running tests."

    def exit(self):
        self.perforce.finalize()


@pytest.fixture()
def revert_parameters(perforce_workspace):
    params = DiffParameters(perforce_workspace)
    yield params
    params.exit()


def test_p4_c_and_revert(revert_parameters):  # pylint: disable = too-many-locals
    parameters = revert_parameters

    test_dir = parameters.env.root_directory.ensure("test_files", dir=True)

    def create_file(filename):
        cur_file = test_dir.join(filename)
        parameters.env.p4.run("add", str(cur_file))
        parameters.env.p4.run("edit", str(cur_file))
        cur_file.write("import os\n\nprint('File {0} has no special modifiers.')\n"
                       "print(os.name)\nprint(os.getcwd())\nprint(os.strerror(3))\n"
                       "print('File change type: {0}')\n".format(filename))

    create_file("edit")
    create_file("move")
    create_file("rename")
    create_file("integrate")
    create_file("integrated")
    create_file("branch")
    create_file("delete")

    change = parameters.env.p4.run_change("-o")[0]
    change["Description"] = "Submit test files"
    parameters.env.p4.run_submit(change)

    # open for edit for edit, move/add and move/rename files
    for cur_file in [test_dir.join("edit"), test_dir.join("move"), test_dir.join("rename")]:
        parameters.env.p4.run("edit", str(cur_file))

    # edit
    test_dir.join("edit").write("import os\n\nprint('File %s has no special modifiers.')\n"
                                "print(os.name)\nprint(os.getegid())\nprint(os.ctermid())\n"
                                "print('File change type: %s')\n" % (test_dir.join("edit"), "edit"))

    # move, rename
    parameters.env.p4.run("move", test_dir + "/move", test_dir + "/moved/move")
    parameters.env.p4.run("rename", test_dir + "/rename", test_dir + "/renamed_rename")
    # integrate
    parameters.env.p4.run("integrate", test_dir + "/integrate", test_dir + "/integrated")
    parameters.env.p4.run("resolve", "-at")
    # branch
    parameters.env.p4.run("integrate", test_dir + "/branch", test_dir + "/moved/branch_to")
    # delete
    parameters.env.p4.run("delete", test_dir + "/delete")
    # add
    add = test_dir.join("add")
    add.write("\nprint('new file')\nprint('not in repo, only for shelve.')")
    parameters.env.p4.run("add", add)

    # make change
    change = parameters.env.p4.fetch_change()
    change["Description"] = "Test revert #1"
    saved_change = parameters.env.p4.save_change(change)[0].split()[1]

    shelve = parameters.env.p4.run_shelve("-fc", saved_change)[0]

    diff, is_files_opened = parameters.run_diff(shelve)
    assert not is_files_opened

    new_test_dir = str(test_dir).replace("workspace", "new_workspace")
    new_temp = new_test_dir.replace("new_workspace", "new_workspace/new_temp")
    expected_path = [
        ("test_files/add", new_temp + "/add", None),
        (None, None, new_test_dir + '/delete'),
        ("test_files/edit", new_temp + "/edit", new_test_dir + "/edit"),
        ("test_files/integrated", new_temp + "/integrated", new_test_dir + "/integrated"),
        ("test_files/moved/branch_to", new_temp + "/moved/branch_to", None),
        ("test_files/moved/move", new_temp + "/moved/move", new_test_dir + "/move"),
        ("test_files/renamed_rename", new_temp + "/renamed_rename", new_test_dir + "/rename")
    ]

    for result, expected in zip(diff, expected_path):
        assert result == expected
