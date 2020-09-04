# pylint: disable = redefined-outer-name

import git
import pytest

from universum import __main__
from . import git_utils, perforce_utils, utils


@pytest.fixture
def unicode_dir(tmpdir):
    yield tmpdir.mkdir("Юніко́д з пробелами")


@pytest.mark.parametrize("vcs", ["git", "p4"])
@pytest.mark.parametrize("test_type", ["main", "poll", "submit"])
def test_unicode(vcs, test_type, perforce_workspace, git_client, unicode_dir):
    if vcs == "git":
        # change git client root dir to unicode path
        work_dir = unicode_dir.mkdir("client")
        git_client.repo = git.Repo.clone_from(git_client.server.url, work_dir)
        git_client.root_directory = work_dir

        env = git_utils.GitEnvironment(git_client, unicode_dir, test_type=test_type)
    elif vcs == "p4":
        # change workspace root dir to unicode path
        root = unicode_dir.mkdir("workspace")
        client = perforce_workspace.p4.fetch_client(perforce_workspace.client_name)
        client["Root"] = str(root)
        perforce_workspace.root_directory = root
        perforce_workspace.p4.save_client(client)
        perforce_workspace.p4.run_sync("-f", "//depot/...")

        env = perforce_utils.P4Environment(perforce_workspace, unicode_dir, test_type=test_type)
    else:
        assert False, "Unsupported vcs type"

    if test_type == "submit":
        temp_file = env.vcs_cooking_dir.join(utils.randomize_name("new_file") + ".txt")
        temp_file.write("This is a new file" + "\n")
        env.settings.Submit.reconcile_list = [str(temp_file)]

    res = __main__.run(env.settings)
    assert res == 0


def test_unicode_main_local_vcs(unicode_dir):
    work_dir = unicode_dir.mkdir("local_sources")
    work_dir.join("source_file").write("Source file contents")

    env = utils.TestEnvironment(unicode_dir, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(work_dir)

    res = __main__.run(env.settings)
    assert res == 0
