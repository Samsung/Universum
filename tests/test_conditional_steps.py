# pylint: disable = invalid-name, redefined-outer-name

import re
import pathlib
from typing import Generator, AnyStr, List, Optional

import pytest

from universum.configuration_support import Step

from .utils import LocalTestEnvironment


class StepsInfo:
    conditional_step: Step
    true_branch_step: Optional[Step]
    false_branch_step: Optional[Step]
    is_conditional_step_passed: bool


class ConditionalStepsTestEnv(LocalTestEnvironment):

    def __init__(self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
        super().__init__(tmp_path, "main")
        self.capsys = capsys

    def build_conditional_steps_info(self, is_conditional_step_passed: bool) -> StepsInfo:
        steps_info: StepsInfo = StepsInfo()

        steps_info.conditional_step = self._build_conditional_step(is_conditional_step_passed)
        steps_info.true_branch_step = self._build_true_branch_step()
        steps_info.false_branch_step = self._build_false_branch_step()
        steps_info.is_conditional_step_passed = is_conditional_step_passed

        return steps_info

    def create_step_artifact(self, step: Step, is_report_artifact: bool = False) -> None:
        file_name: str = step.report_artifacts if is_report_artifact else step.artifacts
        artifact_path: pathlib.Path = self.src_dir / file_name
        artifact_path.touch()

    def check_success(self, steps_info: StepsInfo) -> None:
        self._write_config_file(steps_info)
        self.run()

        captured: pytest.CaptureResult[AnyStr] = self.capsys.readouterr()
        conditional_succeeded_regexp: str = r"\] conditional.*Success.*\|   5\.2"
        assert re.search(conditional_succeeded_regexp, captured.out, re.DOTALL)

        self._check_conditional_step_artifacts_present(steps_info)
        self._check_executed_step_artifacts_present(steps_info)
        self._check_not_executed_step_artifacts_absent(steps_info)

    def check_fail(self, steps_info: StepsInfo) -> None:
        self._write_config_file(steps_info)
        self.run(expect_failure=True)

    def _build_conditional_step(self, is_conditional_step_passed: bool) -> Step:
        conditional_step_name: str = "conditional"
        conditional_step_artifact: str = f"{conditional_step_name}_artifact"
        conditional_step_report_artifact: str = f"{conditional_step_name}_report_artifact"
        conditional_step_exit_code: int = 0 if is_conditional_step_passed else 1
        return Step(name=conditional_step_name,
                    command=self._build_step_command(
                        files_to_create=[conditional_step_artifact, conditional_step_report_artifact],
                        exit_code=conditional_step_exit_code),
                    artifacts=conditional_step_artifact,
                    report_artifacts=conditional_step_report_artifact)

    def _build_true_branch_step(self) -> Step:
        true_branch_step_name: str = "true_branch"
        true_branch_step_artifact: str = f"{true_branch_step_name}_artifact"
        true_branch_step_report_artifact: str = f"{true_branch_step_name}_report_artifact"
        return Step(name=true_branch_step_name,
                    command=self._build_step_command(
                        files_to_create=[true_branch_step_artifact, true_branch_step_report_artifact],
                        exit_code=0),
                    artifacts=true_branch_step_artifact,
                    report_artifacts=true_branch_step_report_artifact)

    def _build_false_branch_step(self) -> Step:
        false_branch_step_name: str = "false_branch"
        false_branch_step_artifact: str = f"{false_branch_step_name}_artifact"
        false_branch_step_report_artifact: str = f"{false_branch_step_name}_report_artifact"
        return Step(name=false_branch_step_name,
                    command=self._build_step_command(
                        files_to_create=[false_branch_step_artifact, false_branch_step_report_artifact],
                        exit_code=0),
                    artifacts=false_branch_step_artifact,
                    report_artifacts=false_branch_step_report_artifact)

    @staticmethod
    def _build_step_command(files_to_create, exit_code) -> List[str]:
        commands: List[str] = []
        for f in files_to_create:
            commands.append(f"touch {f}")
        commands.append(f"exit {exit_code}")
        return ["bash", "-c", ";".join(commands)]

    def _write_config_file(self, steps_info) -> None:
        true_branch_step: str = f"Configuration([Step(**{str(steps_info.true_branch_step)})])" \
            if steps_info.true_branch_step else "None"
        false_branch_step: str = f"Configuration([Step(**{str(steps_info.false_branch_step)})])" \
            if steps_info.false_branch_step else "None"
        config_lines: List[str] = [
            "from universum.configuration_support import Configuration, Step",
            f"true_branch_step = {true_branch_step}",
            f"false_branch_step = {false_branch_step}",
            f"conditional_step = Step(**{str(steps_info.conditional_step)})",

            # `true/false_branch_steps` should be Python objects from this script
            "conditional_step.is_conditional = True",
            "conditional_step.if_succeeded = true_branch_step",
            "conditional_step.if_failed = false_branch_step",

            "configs = Configuration([conditional_step])"
        ]
        config: str = "\n".join(config_lines)

        self.configs_file.write_text(config, "utf-8")

    def _check_conditional_step_artifacts_present(self, steps_info: StepsInfo) -> None:
        conditional_step: Step = steps_info.conditional_step
        self._check_artifacts_presence(conditional_step, is_presence_expected=True)

    def _check_executed_step_artifacts_present(self, steps_info: StepsInfo) -> None:
        executed_step: Optional[Step] = steps_info.true_branch_step if steps_info.is_conditional_step_passed \
            else steps_info.false_branch_step
        self._check_artifacts_presence(executed_step, is_presence_expected=True)

    def _check_not_executed_step_artifacts_absent(self, steps_info: StepsInfo) -> None:
        not_executed_step: Optional[Step] = steps_info.false_branch_step if steps_info.is_conditional_step_passed \
            else steps_info.true_branch_step
        self._check_artifacts_presence(not_executed_step, is_presence_expected=False)

    def _check_artifacts_presence(self, step: Optional[Step], is_presence_expected: bool):
        if not step:  # branch step can be not set
            return
        for artifact in [step.artifacts, step.report_artifacts]:
            artifact_path: pathlib.Path = self.artifact_dir / artifact
            assert artifact_path.exists() == is_presence_expected


@pytest.fixture()
def test_env(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> Generator[ConditionalStepsTestEnv, None, None]:
    yield ConditionalStepsTestEnv(tmp_path, capsys)


def test_conditional_true_branch(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=True)
    test_env.check_success(steps_info)


def test_conditional_false_branch(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=False)
    test_env.check_success(steps_info)


# https://github.com/Samsung/Universum/issues/744
# Artifact will be collected only from the second executed step, the first one will be overwritten
# Skipping checking file content to not overload tests with additional logic for incorrect behaviour check
def test_same_artifact(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=True)

    assert steps_info.true_branch_step
    steps_info.true_branch_step.command = steps_info.conditional_step.command
    steps_info.true_branch_step.artifacts = steps_info.conditional_step.artifacts
    steps_info.true_branch_step.report_artifacts = steps_info.conditional_step.report_artifacts

    test_env.check_success(steps_info)


def test_true_branch_chosen_but_absent(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=True)
    steps_info.true_branch_step = None
    test_env.check_success(steps_info)


def test_false_branch_chosen_but_absent(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=False)
    steps_info.false_branch_step = None
    test_env.check_success(steps_info)


@pytest.mark.parametrize("is_branch_step", [True, False])
@pytest.mark.parametrize("prebuild_clean", [True, False])
@pytest.mark.parametrize("is_report_artifact", [True, False])
def test_prebuild_clean(test_env: ConditionalStepsTestEnv,
                        is_branch_step: bool,
                        prebuild_clean: bool,
                        is_report_artifact: bool) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=True)

    assert steps_info.true_branch_step
    step: Step = steps_info.true_branch_step if is_branch_step else steps_info.conditional_step
    step.artifact_prebuild_clean = prebuild_clean
    test_env.create_step_artifact(step, is_report_artifact)

    if prebuild_clean:
        test_env.check_success(steps_info)
    else:
        test_env.check_fail(steps_info)
