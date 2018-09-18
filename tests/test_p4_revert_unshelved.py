# -*- coding: UTF-8 -*-

import os.path

from _universum.lib.gravity import define_arguments_recursive
import _universum.lib.module_arguments

from _universum.lib.gravity import construct_component
from _universum.modules.vcs import perforce_vcs


def test_p4_copy_and_revert_for_opened_for_edit_file(perforce_workspace):
    edit_file = perforce_workspace.nonwritable_file
    perforce_workspace.p4.run("edit", str(edit_file))
    with open(str(edit_file), "w") as f:
        f.write("Text for file in checkout.\nNew change.")

    change = perforce_workspace.p4.fetch_change()
    change["Description"] = "Test revert #1"
    ret = perforce_workspace.p4.save_change(change)[0].split()[1]

    shelve = perforce_workspace.p4.run_shelve("-fc", ret)[0]

    parser = _universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(perforce_vcs.PerforceMainVcs, parser)
    settings = parser.parse_args(["-ot", "term",
                                  "-p4p", perforce_workspace.p4.port,
                                  "-p4u", perforce_workspace.p4.user,
                                  "-p4P", perforce_workspace.p4.password,
                                  "-p4c", perforce_workspace.client_name,
                                  "-p4d", perforce_workspace.depot,
                                  "--project-root", str(perforce_workspace.root_directory),
                                  "-p4s", shelve["change"]])
    perforce = construct_component(perforce_vcs.PerforceMainVcs, settings)
    perforce.p4 = perforce_workspace.p4
    perforce.expand_workspace_parameters()
    perforce.unshelve()
    copy_revert = perforce.copy_cl_files_and_revert()

    assert str(copy_revert) == "{'" + os.path.basename(str(edit_file)) + "': [Match(a=1, b=2, size=0)]}"
