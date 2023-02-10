# pylint: disable = redefined-outer-name

import inspect
import os
import pathlib
import zipfile
from typing import Generator, Callable

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
        self.artifact_in_dir: pathlib.Path = self.artifact_dir / self.dir_name / self.artifact_name

    def write_config_file(self, artifact_prebuild_clean: bool) -> None:
        artifact_in_dir = f"{self.dir_name}/{self.artifact_name}"
        config: str = inspect.cleandoc(f"""
            from universum.configuration_support import Configuration, Step
            step_with_file = Step(
                name='Step with file',
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

    def create_artifacts_dir(self, directory: pathlib.Path) -> None:
        precreated_artifacts_dir: pathlib.Path = directory / self.dir_name
        precreated_artifacts_dir.mkdir()
        self.create_artifact_file(precreated_artifacts_dir)

    def check_artifact_present(self, path: pathlib.Path) -> None:
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            content: str = f.read().replace("\n", "")
            assert content == self.artifact_content

    def check_artifact_absent(self) -> None:
        assert not os.path.exists(self.artifact_path)

    def check_dir_zip_artifact_present(self) -> None:
        assert os.path.exists(self.dir_archive)
        with zipfile.ZipFile(self.dir_archive) as dir_zip:
            assert self.artifact_name in dir_zip.namelist()
            with dir_zip.open(self.artifact_name) as f:
                content: str = f.read().decode(encoding="utf-8").replace("\n", "")
                assert content == self.artifact_content

    def check_dir_artifact_absent(self) -> None:
        assert not os.path.exists(self.dir_archive)


@pytest.fixture()
def test_env(tmp_path: pathlib.Path) -> Generator[ArtifactsTestEnvironment, None, None]:
    yield ArtifactsTestEnvironment(tmp_path)


class ArtifactsTestData:
    no_archive: bool
    artifact_check_func: Callable[[ArtifactsTestEnvironment], None]

    def __init__(self, no_archive, artifact_check_func) -> None:
        self.no_archive = no_archive
        self.artifact_check_func = artifact_check_func


@pytest.mark.parametrize("prebuild_clean", [True, False])
def test_no_artifact(test_env: ArtifactsTestEnvironment,
                     prebuild_clean: bool) -> None:
    test_env.write_config_file(artifact_prebuild_clean=prebuild_clean)
    test_env.run()
    test_env.check_artifact_present(test_env.artifact_path)


def test_artifact_in_sources_prebuild_clean(test_env: ArtifactsTestEnvironment) -> None:
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifact_file(test_env.src_dir)
    test_env.run()
    test_env.check_artifact_present(test_env.artifact_path)


def test_artifact_in_sources_no_prebuild_clean(test_env: ArtifactsTestEnvironment,
                                               stdout_checker: FuzzyCallChecker) -> None:
    test_env.write_config_file(artifact_prebuild_clean=False)
    test_env.create_artifact_file(test_env.src_dir)
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("already exist in '/.*' directory", is_regexp=True)
    test_env.check_artifact_absent()


@pytest.mark.parametrize("test_data",
                         [ArtifactsTestData(False, lambda env: env.check_dir_zip_artifact_present()),
                          ArtifactsTestData(True, lambda env: env.check_artifact_present(env.artifact_in_dir))])
def test_dir_artifact_in_sources_prebuild_clean(test_env: ArtifactsTestEnvironment,
                                                test_data: ArtifactsTestData) -> None:
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifacts_dir(test_env.src_dir)
    test_env.settings.ArtifactCollector.no_archive = test_data.no_archive
    test_env.run()
    test_data.artifact_check_func(test_env)


def test_dir_artifact_in_sources_no_prebuild_clean(test_env: ArtifactsTestEnvironment,
                                                   stdout_checker: FuzzyCallChecker) -> None:
    test_env.write_config_file(artifact_prebuild_clean=False)
    test_env.create_artifacts_dir(test_env.src_dir)
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("already exist in '/.*' directory", is_regexp=True)
    test_env.check_dir_artifact_absent()


@pytest.mark.parametrize("prebuild_clean", [True, False])
def test_artifact_in_artifacts_dir(test_env: ArtifactsTestEnvironment,
                                   stdout_checker: FuzzyCallChecker,
                                   prebuild_clean: bool) -> None:
    test_env.write_config_file(artifact_prebuild_clean=prebuild_clean)
    test_env.create_artifact_file(test_env.artifact_dir)
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("already present in artifact directory")
