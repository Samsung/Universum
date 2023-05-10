# pylint: disable = redefined-outer-name

import inspect
import pathlib
import zipfile
from typing import Generator

import pytest

from .utils import LocalTestEnvironment
from .conftest import FuzzyCallChecker


class ArtifactsTestEnvironment(LocalTestEnvironment):

    def __init__(self, tmp_path: pathlib.Path, test_type: str) -> None:
        super().__init__(tmp_path, test_type)
        self.artifact_name: str = "artifact"
        self.artifact_path: pathlib.Path = self.artifact_dir / self.artifact_name
        self.artifact_name_with_suffix = f"{self.artifact_name}_suffix"
        self.artifact_path_with_suffix: pathlib.Path = self.artifact_dir / self.artifact_name_with_suffix
        self.artifact_content: str = "artifact content"
        self.dir_name: str = "artifacts_test_dir"
        self.dir_archive: pathlib.Path = self.artifact_dir / f"{self.dir_name}.zip"
        self.artifact_in_dir: pathlib.Path = self.artifact_dir / self.dir_name / self.artifact_name

    def write_config_file(self, artifact_prebuild_clean: bool, is_report_artifact: bool = False) -> None:
        artifact_in_dir: str = f"{self.dir_name}/{self.artifact_name}"
        artifacts_key: str = "report_artifacts" if is_report_artifact else "artifacts"
        config: str = inspect.cleandoc(f"""
            from universum.configuration_support import Configuration, Step
            step_with_file = Step(
                name='Step with file',
                command=['bash', '-c', 'echo "{self.artifact_content}" > {self.artifact_name}'],
                {artifacts_key}='{self.artifact_name}',
                artifact_prebuild_clean={artifact_prebuild_clean})
            step_with_dir = Step(
                name='Step with directory',
                command=['bash', '-c', 'mkdir {self.dir_name}; echo "{self.artifact_content}" > {artifact_in_dir}'],
                {artifacts_key}='{self.dir_name}',
                artifact_prebuild_clean={artifact_prebuild_clean})
            configs = Configuration([step_with_file, step_with_dir])
        """)
        self.store_config_to_file(config)

    def write_config_file_wildcard(self, artifact_prebuild_clean: bool) -> None:
        config: str = inspect.cleandoc(f"""
            from universum.configuration_support import Configuration, Step
            step = Step(
                name='Step',
                command=['bash', '-c', 
                         'echo "{self.artifact_content}" > {self.artifact_name};'
                         'echo "{self.artifact_content}" > {self.artifact_name_with_suffix}'],
                artifacts='{self.artifact_name}*',
                artifact_prebuild_clean={artifact_prebuild_clean})
            configs = Configuration([step])
        """)
        self.store_config_to_file(config)

    def store_config_to_file(self, config: str):
        self.configs_file.write_text(config, "utf-8")

    def create_artifact_file(self, directory: pathlib.Path, file_name: str, is_zip: bool = False) -> None:
        artifact_name: str = f"{file_name}.zip" if is_zip else file_name
        precreated_artifact: pathlib.Path = directory / artifact_name
        with open(precreated_artifact, "w", encoding="utf-8") as f:
            f.write("pre-created artifact content")

    def create_artifacts_dir(self, directory: pathlib.Path) -> None:
        precreated_artifacts_dir: pathlib.Path = directory / self.dir_name
        precreated_artifacts_dir.mkdir()
        self.create_artifact_file(precreated_artifacts_dir, self.artifact_name)

    def check_artifact_present(self, path: pathlib.Path) -> None:
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            content: str = f.read().replace("\n", "")
            assert content == self.artifact_content

    def check_artifact_absent(self) -> None:
        assert not self.artifact_path.exists()

    def check_dir_zip_artifact_present(self) -> None:
        assert self.dir_archive.exists()
        with zipfile.ZipFile(self.dir_archive) as dir_zip:
            assert self.artifact_name in dir_zip.namelist()
            with dir_zip.open(self.artifact_name) as f:
                content: str = f.read().decode(encoding="utf-8").replace("\n", "")
                assert content == self.artifact_content

    def check_dir_zip_artifact_absent(self) -> None:
        assert not self.dir_archive.exists()


@pytest.fixture()
def test_env(tmp_path: pathlib.Path) -> Generator[ArtifactsTestEnvironment, None, None]:
    yield ArtifactsTestEnvironment(tmp_path, "main")


@pytest.mark.parametrize("prebuild_clean", [True, False])
def test_no_artifact(test_env: ArtifactsTestEnvironment,
                     prebuild_clean: bool) -> None:
    test_env.write_config_file(artifact_prebuild_clean=prebuild_clean)
    test_env.run()
    test_env.check_artifact_present(test_env.artifact_path)


@pytest.mark.parametrize("test_type", ["main", "nonci"])
@pytest.mark.parametrize("is_report_artifact", [True, False])
def test_artifact_in_sources_prebuild_clean(tmp_path: pathlib.Path,
                                            is_report_artifact: bool,
                                            test_type: str) -> None:
    test_env: ArtifactsTestEnvironment = ArtifactsTestEnvironment(tmp_path, test_type)
    test_env.write_config_file(artifact_prebuild_clean=True, is_report_artifact=is_report_artifact)
    test_env.create_artifact_file(test_env.src_dir, test_env.artifact_name)
    test_env.run()
    test_env.check_artifact_present(test_env.artifact_path)


@pytest.mark.parametrize("test_type", ["main", "nonci"])
@pytest.mark.parametrize("is_report_artifact", [True, False])
def test_artifact_in_sources_no_prebuild_clean(tmp_path: pathlib.Path,
                                               stdout_checker: FuzzyCallChecker,
                                               is_report_artifact: bool,
                                               test_type: str) -> None:
    test_env: ArtifactsTestEnvironment = ArtifactsTestEnvironment(tmp_path, test_type)
    test_env.write_config_file(artifact_prebuild_clean=False, is_report_artifact=is_report_artifact)
    test_env.create_artifact_file(test_env.src_dir, test_env.artifact_name)
    if test_type == "main":
        test_env.run(expect_failure=True)
        stdout_checker.assert_has_calls_with_param("already exist in '/.*' directory", is_regexp=True)
        test_env.check_artifact_absent()
    elif test_type == "nonci":
        test_env.run()
        test_env.check_artifact_present(test_env.artifact_path)
    else:
        pytest.fail(f"Unexpected type type: {test_type}")


@pytest.mark.parametrize("no_archive", [False, True])
def test_dir_artifact_in_sources_prebuild_clean(test_env: ArtifactsTestEnvironment,
                                                no_archive: bool) -> None:
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifacts_dir(test_env.src_dir)
    test_env.settings.ArtifactCollector.no_archive = no_archive
    test_env.run()
    if no_archive:
        test_env.check_artifact_present(test_env.artifact_in_dir)
    else:
        test_env.check_dir_zip_artifact_present()


def test_dir_artifact_in_sources_no_prebuild_clean(test_env: ArtifactsTestEnvironment,
                                                   stdout_checker: FuzzyCallChecker) -> None:
    test_env.write_config_file(artifact_prebuild_clean=False)
    test_env.create_artifacts_dir(test_env.src_dir)
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("already exist in '/.*' directory", is_regexp=True)
    test_env.check_dir_zip_artifact_absent()


@pytest.mark.parametrize("is_zip", [True, False])
@pytest.mark.parametrize("is_dir", [True, False])
@pytest.mark.parametrize("prebuild_clean", [True, False])
def test_artifact_in_artifacts_dir(test_env: ArtifactsTestEnvironment,
                                       stdout_checker: FuzzyCallChecker,
                                       is_zip: bool,
                                       is_dir: bool,
                                       prebuild_clean: bool) -> None:
    test_env.write_config_file(artifact_prebuild_clean=prebuild_clean)
    artifact_name: str = test_env.dir_name if is_dir else test_env.artifact_name
    test_env.create_artifact_file(test_env.artifact_dir, artifact_name, is_zip)
    test_env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("already present in artifact directory")


def test_zip_artifact_no_archive(test_env: ArtifactsTestEnvironment) -> None:
    test_env.settings.ArtifactCollector.no_archive = True
    test_env.write_config_file(artifact_prebuild_clean=True)
    test_env.create_artifact_file(test_env.artifact_dir, test_env.dir_name, is_zip=True)
    test_env.run()
    test_env.check_artifact_present(test_env.artifact_in_dir)


def test_wildcard(test_env: ArtifactsTestEnvironment) -> None:
    test_env.write_config_file_wildcard(artifact_prebuild_clean=True)
    test_env.create_artifact_file(test_env.src_dir, test_env.artifact_name)
    test_env.create_artifact_file(test_env.src_dir, test_env.artifact_name_with_suffix)
    test_env.run()
    test_env.check_artifact_present(test_env.artifact_path)
    test_env.check_artifact_present(test_env.artifact_path_with_suffix)
