# pylint: disable = invalid-name, redefined-outer-name

import re
import pathlib
from typing import Generator, AnyStr, List, Optional

import pytest

from universum.configuration_support import Step, Configuration

from .utils import LocalTestEnvironment


class StepsInfo:
    conditional_step: Step
    true_branch_steps: Optional[List[Step]]
    false_branch_steps: Optional[List[Step]]
    steps_after_conditional: List[Step]
    is_conditional_step_passed: bool


class ConditionalStepsTestEnv(LocalTestEnvironment):

    def __init__(self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
        super().__init__(tmp_path, "main")
        self.capsys = capsys
        self.captured_out: pytest.CaptureResult[AnyStr] = None

    def build_conditional_steps_info(self, is_conditional_step_passed: bool) -> StepsInfo:
        steps_info: StepsInfo = StepsInfo()

        steps_info.conditional_step = self._build_conditional_step(is_conditional_step_passed)
        steps_info.true_branch_steps = self._build_true_branch_steps()
        steps_info.false_branch_steps = self._build_false_branch_steps()
        steps_info.steps_after_conditional = self._build_steps_after_conditional()
        steps_info.is_conditional_step_passed = is_conditional_step_passed

        return steps_info

    def create_step_artifact(self, step: Step, is_report_artifact: bool = False) -> None:
        file_name: str = step.report_artifacts if is_report_artifact else step.artifacts
        artifact_path: pathlib.Path = self.src_dir / file_name
        artifact_path.touch()

    def check_success(self, steps_info: StepsInfo) -> None:
        self._write_config_file(steps_info)
        self.run()

        self.captured_out = self.capsys.readouterr()
        conditional_succeeded_regexp: str = r"\] conditional.*Success.*\|   5\.2"
        assert re.search(conditional_succeeded_regexp, self.captured_out.out, re.DOTALL)

        self._check_conditional_step_artifacts_present(steps_info)
        self._check_executed_step_artifacts_present(steps_info)
        self._check_not_executed_step_artifacts_absent(steps_info)
        self._check_steps_after_conditional_artifacts_present(steps_info)

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

    def _build_true_branch_steps(self) -> List[Step]:
        return self._build_steps_list(["true_branch", "true_branch_dependent1", "true_branch_dependent2"])

    def _build_false_branch_steps(self) -> List[Step]:
        return self._build_steps_list(["false_branch", "false_branch_dependent"])

    def _build_steps_after_conditional(self) -> List[Step]:
        return self._build_steps_list(["step_after_conditional"])

    def _build_steps_list(self, step_names: List[str]) -> List[Step]:
        steps = []
        for step_name in step_names:
            step_artifact: str = f"{step_name}_artifact"
            step_report_artifact: str = f"{step_name}_report_artifact"
            steps.append(Step(name=step_name,
                              command=self._build_step_command(
                                  files_to_create=[step_artifact, step_report_artifact],
                                  exit_code=0),
                              artifacts=step_artifact,
                              report_artifacts=step_report_artifact))
        return steps

    @staticmethod
    def _build_step_command(files_to_create, exit_code) -> List[str]:
        commands: List[str] = []
        for f in files_to_create:
            commands.append(f"touch {f}")
        commands.append(f"exit {exit_code}")
        return ["bash", "-c", ";".join(commands)]

    def _write_config_file(self, steps_info) -> None:
        true_branch_config = self._build_configuration_string(steps_info.true_branch_steps)
        false_branch_config = self._build_configuration_string(steps_info.false_branch_steps)
        conditional_children_config = self._build_configuration_string(steps_info.conditional_step.children)
        config_after_conditional = self._build_configuration_string(steps_info.steps_after_conditional)
        steps_info.conditional_step.children = None  # will be set in config text
        config_lines: List[str] = [
            "from universum.configuration_support import Configuration, Step",
            f"true_branch_config = {true_branch_config}",
            f"false_branch_config = {false_branch_config}",
            f"conditional_children_config = {conditional_children_config}",
            f"conditional_step = Step(**{str(steps_info.conditional_step)})",
            f"config_after_conditional = {config_after_conditional}",

            # `true/false_branch_steps` should be Python objects from this script
            "conditional_step.is_conditional = True",
            "conditional_step.if_succeeded = true_branch_config",
            "conditional_step.if_failed = false_branch_config",
            "conditional_step.children = conditional_children_config",

            "configs = Configuration([conditional_step]) + config_after_conditional"
        ]
        config: str = "\n".join(config_lines)

        self.configs_file.write_text(config, "utf-8")

    @staticmethod
    def _build_configuration_string(steps: Optional[List[Step]]) -> str:
        if not steps:
            return "None"
        steps_strings: List[str] = [f"Step(**{str(step)})" for step in steps]
        steps_list_string: str = ", ".join(steps_strings)
        return f"Configuration([{steps_list_string}])"

    def _check_conditional_step_artifacts_present(self, steps_info: StepsInfo) -> None:
        conditional_step: Step = steps_info.conditional_step
        self._check_artifacts_presence([conditional_step], is_presence_expected=True)

    def _check_executed_step_artifacts_present(self, steps_info: StepsInfo) -> None:
        executed_steps: Optional[List[Step]] = steps_info.true_branch_steps \
            if steps_info.is_conditional_step_passed else steps_info.false_branch_steps
        self._check_artifacts_presence(executed_steps, is_presence_expected=True)

    def _check_not_executed_step_artifacts_absent(self, steps_info: StepsInfo) -> None:
        not_executed_steps: Optional[List[Step]] = steps_info.false_branch_steps \
            if steps_info.is_conditional_step_passed else steps_info.true_branch_steps
        self._check_artifacts_presence(not_executed_steps, is_presence_expected=False)

    def _check_steps_after_conditional_artifacts_present(self, steps_info: StepsInfo) -> None:
        steps_after_conditional: List[Step] = steps_info.steps_after_conditional
        self._check_artifacts_presence(steps_after_conditional, is_presence_expected=True)

    def _check_artifacts_presence(self, steps: Optional[List[Step]], is_presence_expected: bool):
        if not steps:  # branch configuration can be not set
            return
        for step in steps:
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

    assert steps_info.true_branch_steps
    steps_info.true_branch_steps[0].command = steps_info.conditional_step.command
    steps_info.true_branch_steps[0].artifacts = steps_info.conditional_step.artifacts
    steps_info.true_branch_steps[0].report_artifacts = steps_info.conditional_step.report_artifacts

    test_env.check_success(steps_info)


def test_true_branch_chosen_but_absent(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=True)
    steps_info.true_branch_steps = None
    test_env.check_success(steps_info)


def test_false_branch_chosen_but_absent(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=False)
    steps_info.false_branch_steps = None
    test_env.check_success(steps_info)


@pytest.mark.parametrize("is_branch_step", [True, False])
@pytest.mark.parametrize("prebuild_clean", [True, False])
@pytest.mark.parametrize("is_report_artifact", [True, False])
def test_prebuild_clean(test_env: ConditionalStepsTestEnv,
                        is_branch_step: bool,
                        prebuild_clean: bool,
                        is_report_artifact: bool) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=True)

    assert steps_info.true_branch_steps
    step: Step = steps_info.true_branch_steps[0] if is_branch_step else steps_info.conditional_step
    step.artifact_prebuild_clean = prebuild_clean
    test_env.create_step_artifact(step, is_report_artifact)

    if prebuild_clean:
        test_env.check_success(steps_info)
    else:
        test_env.check_fail(steps_info)


# TODO: implement support of conditional step with children
#  https://github.com/Samsung/Universum/issues/709
def test_conditional_step_with_children(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=True)
    steps_info.conditional_step.children = Configuration([Step(name=" dummy child 1"), Step(name=" dummy child 2")])
    test_env.check_fail(steps_info)


def test_conditional_step_critical(test_env: ConditionalStepsTestEnv) -> None:
    steps_info: StepsInfo = test_env.build_conditional_steps_info(is_conditional_step_passed=False)
    steps_info.conditional_step.critical = True
    test_env.check_success(steps_info)
    assert test_env.captured_out.out
    assert "WARNING" in test_env.captured_out.out
