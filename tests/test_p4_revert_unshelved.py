# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import os
import pytest

import universum
from _universum.lib.gravity import construct_component
from _universum.modules.vcs import perforce_vcs
from . import utils


class DiffParameters(object):
    def __init__(self, perforce_workspace):
        self.perforce_workspace = perforce_workspace

        for env_var in ["P4_PATH", "P4_MAPPINGS"]:
            try:
                del os.environ[env_var]
            except KeyError:
                pass

        # TODO: move this block to utils
        settings = utils.create_empty_settings("main")
        settings.PerforceVcs.port = perforce_workspace.p4.port
        settings.PerforceVcs.user = perforce_workspace.p4.user
        settings.PerforceVcs.password = perforce_workspace.p4.password
        settings.Output.type = "term"
        settings.ProjectDirectory.project_root = str(self.perforce_workspace.root_directory + "/../new_workspace")
        settings.PerforceWithMappings.mappings = [self.perforce_workspace.depot + " /..."]
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
def diff_parameters(perforce_workspace):
    params = None
    try:
        params = DiffParameters(perforce_workspace)
        yield params
    finally:
        if params:
            params.exit()


def test_p4_c_and_revert(diff_parameters):  # pylint: disable = too-many-locals
    p4 = diff_parameters.perforce_workspace.p4
    test_dir = diff_parameters.perforce_workspace.root_directory.ensure("test_files", dir=True)

    def create_file(filename):
        cur_file = test_dir.join(filename)
        p4.run("add", str(cur_file))
        p4.run("edit", str(cur_file))
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

    change = p4.run_change("-o")[0]
    change["Description"] = "Submit test files"
    p4.run_submit(change)

    # open for edit for edit, move/add and move/rename files
    for cur_file in [test_dir.join("edit"), test_dir.join("move"), test_dir.join("rename")]:
        p4.run("edit", str(cur_file))

    # edit
    test_dir.join("edit").write("import os\n\nprint('File %s has no special modifiers.')\n"
                                "print(os.name)\nprint(os.getegid())\nprint(os.ctermid())\n"
                                "print('File change type: %s')\n" % (test_dir.join("edit"), "edit"))

    # move, rename
    p4.run("move", test_dir + "/move", test_dir + "/moved/move")
    p4.run("rename", test_dir + "/rename", test_dir + "/renamed_rename")
    # integrate
    p4.run("integrate", test_dir + "/integrate", test_dir + "/integrated")
    p4.run("resolve", "-at")
    # branch
    p4.run("integrate", test_dir + "/branch", test_dir + "/moved/branch_to")
    # delete
    p4.run("delete", test_dir + "/delete")
    # add
    add = test_dir.join("add")
    add.write("\nprint('new file')\nprint('not in repo, only for shelve.')")
    p4.run("add", add)

    # make change
    change = p4.fetch_change()
    change["Description"] = "Test revert #1"
    saved_change = p4.save_change(change)[0].split()[1]

    shelve = p4.run_shelve("-fc", saved_change)[0]

    diff, is_files_opened = diff_parameters.run_diff(shelve)
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


class RevertEnvironment(utils.TestEnvironment):
    def __init__(self, directory, perforce_workspace):
        self.work_dir = directory
        self.vcs_cooking_dir = perforce_workspace.root_directory
        self.repo_file = perforce_workspace.repo_file
        self.nonwritable_file = perforce_workspace.nonwritable_file
        self.p4 = perforce_workspace.p4
        self.depot = perforce_workspace.depot
        self.configs_file = directory.join("configs.py")

        super(RevertEnvironment, self).__init__(directory, "main")


@pytest.fixture()
def perforce_environment(tmpdir, perforce_workspace):
    yield RevertEnvironment(tmpdir, perforce_workspace)


def test_p4_error_revert(perforce_environment, stdout_checker, capsys):
    p4 = perforce_environment.p4
    p4_file = perforce_environment.repo_file

    settings = perforce_environment.settings
    settings.Vcs.type = "p4"
    settings.Launcher.output = "console"
    settings.PerforceVcs.port = perforce_environment.p4.port
    settings.PerforceVcs.user = perforce_environment.p4.user
    settings.PerforceVcs.password = perforce_environment.p4.password
    settings.PerforceMainVcs.client = "p4_disposable_workspace"
    settings.PerforceMainVcs.force_clean = True
    settings.PerforceWithMappings.project_depot_path = perforce_environment.depot

    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Restrict changes", command=["chmod", "-R", "-w", "."]),
                      dict(name="Check", command=["ls", "-la"])])
""".format(p4_file.basename, p4_file.basename)
    perforce_environment.configs_file.write(config)

    # Prepare SHELVE_CHANGELIST
    p4.run_edit(perforce_environment.depot)
    p4_file.write("This is a change.\n")
    change = p4.fetch_change()
    change["Description"] = "CL for shelving"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)
    settings.PerforceMainVcs.shelve_cls = [shelve_cl]

    result = universum.run(perforce_environment.settings)
    perforce_environment.work_dir.chmod(0777, rec=1)
    perforce_environment.work_dir.remove(rec=1)
    assert result != 0
    stdout_checker.assert_has_calls_with_param("Errors during command execution( \"p4 revert //...\" )")
    assert "[Errno 13] Permission denied" in capsys.readouterr().err
