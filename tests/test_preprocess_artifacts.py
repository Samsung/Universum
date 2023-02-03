# pylint: disable = redefined-outer-name

import inspect
import os
import pathlib
import zipfile
from typing import Generator

import pytest

from .utils import LocalTestEnvironment
from .conftest import FuzzyCallChecker


class ArtifactsTestEnvironment(LocalTestEnvironment):

    def __init__(self, tmp_path: pathlib.Path) -> None:
        super().__init__(tmp_path, "main")
        self.artifact_name: str = "artifact"
        self.artifact_path: pathlib.Path = self.artifact_dir / self.artifact_name
        self.artifact_content: str = "artifact content"
        self.dir_name: str = "artifacts_test_dir"
        self.dir_archive: pathlib.Path = self.artifact_dir / f"{self.dir_name}.zip"

    def write_config_file(self, artifact_prebuild_clean: bool) -> None:
        artifact_in_dir = f"{self.dir_name}/{self.artifact_name}"
        config: str = inspect.cleandoc(f"""
            from universum.configuration_support import Configuration, Step
            step_with_file = Step(name='Step with file',
                                  command=['bash', '-c', 'echo "{self.artifact_content}" > {self.artifact_name}'],
                                  artifacts='{self.artifact_name}',
                                  artifact_prebuild_clean={artifact_prebuild_clean})
            step_with_dir = Step(
                name='Step with directory',
                command=['bash', '-c', 'mkdir {self.dir_name}; echo "{self.artifact_content}" > {artifact_in_dir}'],
                artifacts='{self.dir_name}',
                artifact_prebuild_clean={artifact_prebuild_clean})
            configs = Configuration([step_with_file, step_with_dir])
        """)
        self.configs_file.write_text(config, "utf-8")

    def create_artifact_file(self, directory: pathlib.Path) -> None:
        precreated_artifact: pathlib.Path = directory / self.artifact_name
        with open(precreated_artifact, "w", encoding="utf-8") as f:
            f.write("pre-created artifact content")

    def create_artifacts_dir(self, directory: pathlib.Path):
        precreated_artifacts_dir: pathlib.Path = directory / self.dir_name
        precreated_artifacts_dir.mkdir()
        self.create_artifact_file(precreated_artifacts_dir)

    def check_step_artifact_present(self) -> None:
        assert os.path.exists(self.artifact_path)
        with open(self.artifact_path, encoding="utf-8") as f:
            content: str = f.read().replace("\n", "")
            assert content == self.artifact_content

    def check_step_artifact_absent(self) -> None:
        assert not os.path.exists(self.artifact_path)

    def check_step_dir_artifact_present(self) -> None:
        assert os.path.exists(self.dir_archive)
        dir_zip: zipfile.ZipFile = zipfile.ZipFile(self.dir_archive)
        assert self.artifact_name in dir_zip.namelist()
        with dir_zip.open(self.artifact_name) as f:
            content: str = f.read().decode(encoding="utf-8").replace("\n", "")
            assert content == self.artifact_content


@pytest.fixture()
def test_env(tmp_path: pathlib.Path) -> Generator[ArtifactsTestEnvironment, None, None]:
    yield ArtifactsTestEnvironment(tmp_path)


@pytest.mark.parametrize("prebuild_clean", [True, False])
def test_no_artifact(test_env: ArtifactsTestEnvironment,
                     prebuild_clean: bool) -> None:
    test_env.write_config_file(artifact_prebuild_clean=prebuild_clean)
    test_env.run()
    test_env.check_step_artifact_present()


def test_artifact_in_sources_prebuild_clean(test_env: ArtifactsTestEnvironment) -> None:
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifact_file(test_env.src_dir)
    test_env.run()
    test_env.check_step_artifact_present()


def test_artifact_in_sources_no_prebuild_clean(test_env: ArtifactsTestEnvironment,
                                               stdout_checker: FuzzyCallChecker) -> None:
    test_env.write_config_file(artifact_prebuild_clean=False)
    test_env.create_artifact_file(test_env.src_dir)
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("already exist in '/.*' directory", is_regexp=True)
    test_env.check_step_artifact_absent()


def test_dir_artifact_in_sources_prebuild_clean(test_env: ArtifactsTestEnvironment) -> None:
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifacts_dir(test_env.src_dir)
    test_env.run()
    test_env.check_step_dir_artifact_present()


@pytest.mark.parametrize("prebuild_clean", [True, False])
def test_artifact_in_artifacts_dir(test_env: ArtifactsTestEnvironment,
                                   stdout_checker: FuzzyCallChecker,
                                   prebuild_clean: bool) -> None:
    test_env.write_config_file(artifact_prebuild_clean=prebuild_clean)
    test_env.create_artifact_file(test_env.artifact_dir)
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("already present in artifact directory")
