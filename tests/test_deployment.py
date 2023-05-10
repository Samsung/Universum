from .deployment_utils import UniversumRunner
from .utils import python, simple_test_config


def test_minimal_install(clean_docker_main: UniversumRunner):
    # Run without parameters
    log = clean_docker_main.environment.assert_unsuccessful_execution(f"{python()} -m universum")
    assert "No module named universum" not in log

    # Run locally
    log = clean_docker_main.run(simple_test_config, force_installed=True)
    assert clean_docker_main.local.repo_file.name in log

    # Run from Git
    clean_docker_main.clean_artifacts()
    log = clean_docker_main.run(simple_test_config, vcs_type="git", force_installed=True)
    assert clean_docker_main.git.repo_file.name in log

    # Run from P4
    clean_docker_main.clean_artifacts()
    log = clean_docker_main.run(simple_test_config, vcs_type="p4", force_installed=True)
    assert clean_docker_main.perforce.repo_file.name in log


def test_minimal_install_with_git_only(clean_docker_main_no_p4: UniversumRunner, capsys):
    # Run from P4
    clean_docker_main_no_p4.run(simple_test_config, vcs_type="p4", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run from git
    clean_docker_main_no_p4.clean_artifacts()
    log = clean_docker_main_no_p4.run(simple_test_config, vcs_type="git", force_installed=True)
    assert clean_docker_main_no_p4.git.repo_file.name in log


def test_minimal_install_plain_ubuntu(clean_docker_main_no_vcs: UniversumRunner, capsys):
    # Run from P4
    clean_docker_main_no_vcs.run(simple_test_config, vcs_type="p4", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run from Git
    clean_docker_main_no_vcs.run(simple_test_config, vcs_type="git", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run locally
    log = clean_docker_main_no_vcs.run(simple_test_config, force_installed=True)
    assert clean_docker_main_no_vcs.local.repo_file.name in log
