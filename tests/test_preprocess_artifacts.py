import inspect
import os
import pathlib

import pytest

from .utils import LocalTestEnvironment
from .conftest import FuzzyCallChecker


class ArtifactsTestEnvironment(LocalTestEnvironment):

    def __init__(self, tmpdir: pathlib.Path):
        super().__init__(tmpdir, "main")
        self.artifact_name: str = "artifact"
        self.artifact_path: pathlib.Path = self.artifact_dir.join(self.artifact_name)
        self.artifact_content: str = "artifact content"

    def write_config_file(self, artifact_prebuild_clean: bool):
        config: str = inspect.cleandoc(f"""
            from universum.configuration_support import Configuration, Step
            step = Step(name='Step', 
                        command=['bash', '-c', 'echo "{self.artifact_content}" > {self.artifact_name}'], 
                        artifacts='{self.artifact_name}', 
                        artifact_prebuild_clean={artifact_prebuild_clean})
            configs = Configuration([step])
        """)
        self.configs_file.write_text(config, "utf-8")

    def check_step_artifact_present(self):
        assert os.path.exists(self.artifact_path)
        with open(self.artifact_path) as f:
            content: str = f.read().replace("\n", "")
            assert content == self.artifact_content

    def check_step_artifact_absent(self):
        assert not os.path.exists(self.artifact_path)

    def create_artifact_file(self):
        precreated_artifact: pathlib.Path = self.src_dir.join(self.artifact_name)
        with open(precreated_artifact, "w") as f:
            f.write("pre-created artifact content")


@pytest.fixture()
def test_env(tmpdir: pathlib.Path):
    yield ArtifactsTestEnvironment(tmpdir)


def test_no_artifact_prebuild_clean(test_env: ArtifactsTestEnvironment):
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.run()
    test_env.check_step_artifact_present()


def test_no_artifact_no_prebuild_clean(test_env: ArtifactsTestEnvironment):
    test_env.write_config_file(artifact_prebuild_clean=False)
    test_env.run()
    test_env.check_step_artifact_present()


def test_existing_artifact_prebuild_clean(test_env: ArtifactsTestEnvironment):
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifact_file()
    test_env.run()
    test_env.check_step_artifact_present()


def test_existing_artifact_no_prebuild_clean(test_env: ArtifactsTestEnvironment, stdout_checker: FuzzyCallChecker):
    test_env.write_config_file(artifact_prebuild_clean=False)
    test_env.create_artifact_file()
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param(f"already exist in '/.*' directory", is_regexp=True)
    test_env.check_step_artifact_absent()