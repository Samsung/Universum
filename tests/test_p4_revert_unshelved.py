# pylint: disable = redefined-outer-name

import os
import pytest

from universum.lib.gravity import construct_component
from universum.modules.vcs.perforce_vcs import PerforceMainVcs
from . import utils
from .perforce_utils import PerforceWorkspace


class DiffParameters:
    def __init__(self, perforce_workspace: PerforceWorkspace):
        self.perforce_workspace: PerforceWorkspace = perforce_workspace

        for env_var in ["P4_PATH", "P4_MAPPINGS"]:
            try:
                del os.environ[env_var]
            except KeyError:
                pass

        # TODO: move this block to utils
        settings = utils.create_empty_settings("main")
        settings.PerforceVcs.port = perforce_workspace.server.port
        settings.PerforceVcs.user = perforce_workspace.server.user
        settings.PerforceVcs.password = perforce_workspace.server.password
        settings.Output.type = "term"
        settings.ProjectDirectory.project_root = str(self.perforce_workspace.root_directory) + "/../new_workspace"
        settings.PerforceWithMappings.mappings = [self.perforce_workspace.depot + " /..."]
        settings.PerforceMainVcs.force_clean = True
        settings.PerforceMainVcs.client = "new_client"

        self.perforce: PerforceMainVcs = construct_component(PerforceMainVcs, settings)

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
def diff_parameters(perforce_workspace: PerforceWorkspace):
    params = None
    try:
        params = DiffParameters(perforce_workspace)
        yield params
    finally:
        if params:
            params.exit()


def test_p4_c_and_revert(diff_parameters):  # pylint: disable = too-many-locals
    p4 = diff_parameters.perforce_workspace.p4
    test_dir = diff_parameters.perforce_workspace.root_directory / "test_files"
    test_dir.mkdir()

    def create_file(filename):
        cur_file = test_dir / filename
        p4.run("add", str(cur_file))
        p4.run("edit", str(cur_file))
        cur_file.write_text(f"import os\n\nprint('File {0} has no special modifiers.')\n"
                       f"print(os.name)\nprint(os.getcwd())\nprint(os.strerror(3))\n"
                       f"print('File change type: {filename}')\n")

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
    for cur_file in [test_dir / "edit", test_dir / "move", test_dir / "rename"]:
        p4.run("edit", str(cur_file))

    # edit
    (test_dir / "edit").write_text(f"import os\n\nprint('File {test_dir / 'edit'} has no special modifiers.')\n"
                                f"print(os.name)\nprint(os.getegid())\nprint(os.ctermid())\n"
                                f"print('File change type: \"edit\"')\n")

    # move, rename
    p4.run("move", test_dir / "move", test_dir / "moved/move")
    p4.run("rename", test_dir / "rename", test_dir / "renamed_rename")
    # integrate
    p4.run("integrate", test_dir / "integrate", test_dir / "integrated")
    p4.run("resolve", "-at")
    # branch
    p4.run("integrate", test_dir / "branch", test_dir / "moved/branch_to")
    # delete
    p4.run("delete", test_dir / "delete")
    # add
    add = test_dir / "add"
    add.write_text("\nprint('new file')\nprint('not in repo, only for shelve.')")
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
