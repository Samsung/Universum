import json
from os import path

from .deployment_utils import UniversumRunner
from .utils import python

config = f"""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Run script", artifacts="output.json",
                              command=["bash", "-c", "{python()} -m universum api file-diff > output.json"])])
"""


def test_error_wrong_environment(docker_main_and_nonci: UniversumRunner):
    cmd = f"{python()} -m universum api file-diff"
    log = docker_main_and_nonci.environment.assert_unsuccessful_execution(cmd)
    assert "Error: Failed to read the 'UNIVERSUM_DATA_FILE' from environment" in log


def test_p4_file_diff(docker_main_with_vcs: UniversumRunner):
    p4 = docker_main_with_vcs.perforce.p4
    p4_directory = docker_main_with_vcs.perforce.root_directory
    p4_file = docker_main_with_vcs.perforce.repo_file

    p4.run_edit(p4_file)
    p4_file.write_text("This line is added to the file.\n")
    p4.run_move(p4_file, p4_directory / "some_new_file_name.txt")
    change = p4.fetch_change()
    change["Description"] = "Rename basic config"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    log = docker_main_with_vcs.run(config, vcs_type="p4", environment=[f"SHELVE_CHANGELIST={shelve_cl}"],
                                   additional_parameters=" --p4-force-clean")
    assert "Module sh got exit code" not in log

    with open(path.join(docker_main_with_vcs.artifact_dir, "output.json"), encoding="utf-8") as f:
        result = json.load(f)

    assert result[0]["action"] == "move/add"
    assert result[0]["repo_path"] == "//depot/some_new_file_name.txt"
    assert result[1]["action"] == "move/delete"
    assert result[1]["repo_path"] == "//depot/writeable_file.txt"


def test_multiple_p4_file_diff(docker_main_with_vcs: UniversumRunner):
    p4 = docker_main_with_vcs.perforce.p4
    p4_directory = docker_main_with_vcs.perforce.root_directory

    for index in range(0, 10000):
        new_file = p4_directory / f"new_file_{index}.txt"
        new_file.write_text(f"This is file #{index}\n")
        p4.run_add(new_file)
    change = p4.fetch_change()
    change["Description"] = "Add 10000 files"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    log = docker_main_with_vcs.run(config, vcs_type="p4", environment=[f"SHELVE_CHANGELIST={shelve_cl}"],
                                   additional_parameters=" --p4-force-clean")
    assert "Module sh got exit code" not in log

    with open(path.join(docker_main_with_vcs.artifact_dir, "output.json"), encoding="utf-8") as f:
        result = json.load(f)
    assert len(result) == 10000
    for entry in result:
        assert entry["action"] == "add"


def test_git_file_diff(docker_main_with_vcs: UniversumRunner):
    repo = docker_main_with_vcs.git.repo
    server = docker_main_with_vcs.git.server
    logger = docker_main_with_vcs.git.logger
    git_directory = docker_main_with_vcs.git.root_directory
    git_file = docker_main_with_vcs.git.repo_file

    repo.git.checkout(server.target_branch)
    repo.git.checkout("new_testing_branch", b=True)
    repo.git.mv(git_file, git_directory / "some_new_file_name.txt")
    change = repo.index.commit("Special commit for testing")
    repo.remotes.origin.push(progress=logger, all=True)

    log = docker_main_with_vcs.run(config, vcs_type="git",
                                   environment=[f"GIT_CHERRYPICK_ID={change}",
                                                f"GIT_REFSPEC={server.target_branch}"])
    assert "Module sh got exit code" not in log

    with open(path.join(docker_main_with_vcs.artifact_dir, "output.json"), encoding="utf-8") as f:
        result = json.load(f)

    assert result[0]["action"] == "rename"
    assert result[0]["repo_path"] == "readme.txt"
    assert 'some_new_file_name.txt' in result[0]["local_path"]


def test_multiple_git_file_diff(docker_main_with_vcs: UniversumRunner):
    repo = docker_main_with_vcs.git.repo
    server = docker_main_with_vcs.git.server
    logger = docker_main_with_vcs.git.logger
    git_directory = docker_main_with_vcs.git.root_directory

    repo.git.checkout(server.target_branch)
    repo.git.checkout("new_testing_branch", b=True)
    files = []
    for index in range(0, 10000):
        new_file = git_directory / f"new_file_{index}.txt"
        new_file.write_text(f"This is file #{index}\n")
        files.append(str(new_file))
    repo.index.add(files)
    change = repo.index.commit("Special commit for testing")
    repo.remotes.origin.push(progress=logger, all=True)

    log = docker_main_with_vcs.run(config, vcs_type="git",
                                   environment=[f"GIT_CHERRYPICK_ID={change}",
                                                f"GIT_REFSPEC={server.target_branch}"])
    assert "Module sh got exit code" not in log

    with open(path.join(docker_main_with_vcs.artifact_dir, "output.json"), encoding="utf-8") as f:
        result = json.load(f)
    assert len(result) == 10000
    for entry in result:
        assert entry["action"] == "add"
