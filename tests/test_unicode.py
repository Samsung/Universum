# pylint: disable = redefined-outer-name

import pathlib
import git
import pytest

from . import utils
from .git_utils import GitClient, GitTestEnvironment
from .perforce_utils import PerforceWorkspace, P4TestEnvironment


@pytest.fixture
def unicode_dir(tmp_path: pathlib.Path):
    unicode_dir_path = tmp_path / "Юніко́д з пробелами"
    unicode_dir_path.mkdir()
    yield unicode_dir_path


@pytest.mark.parametrize("vcs", ["git", "p4"])
@pytest.mark.parametrize("test_type", ["main", "poll", "submit"])
def test_unicode(vcs, test_type, perforce_workspace: PerforceWorkspace, git_client: GitClient, unicode_dir: pathlib.Path):
    env: utils.BaseTestEnvironment
    if vcs == "git":
        # change git client root dir to unicode path
        work_dir = unicode_dir / "client"
        work_dir.mkdir()
        git_client.repo = git.Repo.clone_from(git_client.server.url, work_dir)
        git_client.root_directory = work_dir

        env = GitTestEnvironment(git_client, unicode_dir, test_type=test_type)
    elif vcs == "p4":
        # change workspace root dir to unicode path
        root = unicode_dir / "workspace"
        root.mkdir()
        client = perforce_workspace.p4.fetch_client(perforce_workspace.client_name)
        client["Root"] = str(root)
        perforce_workspace.root_directory = root
        perforce_workspace.p4.save_client(client)
        perforce_workspace.p4.run_sync("-f", "//depot/...")

        env = P4TestEnvironment(perforce_workspace, unicode_dir, test_type=test_type)
    else:
        assert False, "Unsupported vcs type"

    if test_type == "submit":
        file_name = utils.randomize_name("new_file") + ".txt"
        temp_file = env.vcs_client.root_directory / file_name
        temp_file.write_text("This is a new file" + "\n")
        env.settings.Submit.reconcile_list = str(temp_file)

    env.run()


def test_unicode_main_local_vcs(unicode_dir: pathlib.Path):
    work_dir = unicode_dir / "local_sources"
    work_dir.mkdir()
    (work_dir / "source_file").write_text("Source file contents")

    env = utils.LocalTestEnvironment(unicode_dir, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(work_dir)

    env.run()
