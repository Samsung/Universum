import inspect
import os
import pytest

from universum import __main__


@pytest.fixture()
def test_env(tmpdir):
    yield ArtifactsTestEnvironment(tmpdir)


def test_no_artifact_prebuild_clean(test_env):
    test_env.write_config_file(artifact_prebuild_clean=True)
    check_universum_executed_successfully(test_env)
    test_env.check_step_artifact_present()


def test_no_artifact_no_prebuild_clean(test_env):
    test_env.write_config_file(artifact_prebuild_clean=False)
    check_universum_executed_successfully(test_env)
    test_env.check_step_artifact_present()


def test_existing_artifact_prebuild_clean(test_env):
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifact_file()
    check_universum_executed_successfully(test_env)
    test_env.check_step_artifact_present()


def test_existing_artifact_no_prebuild_clean(test_env, stdout_checker):
    test_env.write_config_file(artifact_prebuild_clean=False)
    test_env.create_artifact_file()
    check_universum_failed(test_env, stdout_checker)
    test_env.check_step_artifact_absent()


def check_universum_executed_successfully(test_env):
    return_code = launch_universum(test_env)
    assert return_code == 0


def check_universum_failed(test_env, stdout_checker):
    return_code = launch_universum(test_env)
    assert return_code == 1
    stdout_checker.assert_has_calls_with_param(f"already exist in '/.*' directory", is_regexp=True)


def launch_universum(test_env):
    params = ["-vt", "none",
              "-fsd", str(test_env.tmpdir),
              "-ad", str(test_env.artifacts_dir),
              "--clean-build",
              "-o", "console",
              "-cfg", str(test_env.config_file)]
    return __main__.main(params)


class ArtifactsTestEnvironment:

    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.artifacts_dir = tmpdir.join("artifacts")
        self.artifact_name = "artifact"
        self.artifact_path = self.artifacts_dir.join(self.artifact_name)
        self.config_file = None

    def write_config_file(self, artifact_prebuild_clean):
        config = inspect.cleandoc(f"""
            from universum.configuration_support import Configuration, Step
            step = Step(name='Step', command=['touch', '{self.artifact_name}'], artifacts='{self.artifact_name}', 
                        artifact_prebuild_clean={artifact_prebuild_clean})
            configs = Configuration([step])
        """)
        self.config_file = self.tmpdir.join("configs.py")
        self.config_file.write_text(config, "utf-8")

    def check_step_artifact_present(self):
        assert os.path.exists(self.artifact_path)

    def check_step_artifact_absent(self):
        assert not os.path.exists(self.artifact_path)

    def create_artifact_file(self):
        artifact_path = self.tmpdir.join(self.artifact_name)
        open(artifact_path, "w").close()
