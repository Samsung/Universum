import re
import os

from universum import __main__
from universum.configuration_support import Step


class StepsInfo:
    conditional_step = None
    true_branch_step = None
    false_branch_step = None
    is_conditional_step_passed = False


def test_conditional_true_branch(tmpdir, capsys):
    steps_info = get_conditional_steps_info(is_conditional_step_passed=True)
    check_conditional_step(tmpdir, capsys, steps_info)


def test_conditional_false_branch(tmpdir, capsys):
    steps_info = get_conditional_steps_info(is_conditional_step_passed=False)
    check_conditional_step(tmpdir, capsys, steps_info)


# https://github.com/Samsung/Universum/issues/744
# Artifact will be collected only from the second executed step, the first one will be overwritten
# Skipping checking file content to not overload tests with additional logic for incorrect behaviour check
def test_same_artifact(tmpdir, capsys):
    steps_info = get_conditional_steps_info(is_conditional_step_passed=True)

    steps_info.true_branch_step.command = steps_info.conditional_step.command
    steps_info.true_branch_step.artifacts = steps_info.conditional_step.artifacts
    steps_info.true_branch_step.report_artifacts = steps_info.conditional_step.report_artifacts

    check_conditional_step(tmpdir, capsys, steps_info)


def test_true_branch_chosen_but_absent(tmpdir, capsys):
    steps_info = get_conditional_steps_info(is_conditional_step_passed=True)
    steps_info.true_branch_step = None
    check_conditional_step(tmpdir, capsys, steps_info)


def test_false_branch_chosen_but_absent(tmpdir, capsys):
    steps_info = get_conditional_steps_info(is_conditional_step_passed=False)
    steps_info.false_branch_step = None
    check_conditional_step(tmpdir, capsys, steps_info)


def get_conditional_steps_info(is_conditional_step_passed):
    steps_info = StepsInfo()

    conditional_step_name = "conditional"
    conditional_step_artifact = f"{conditional_step_name}_artifact"
    conditional_step_report_artifact = f"{conditional_step_name}_report_artifact"
    conditional_step_exit_code = 0 if is_conditional_step_passed else 1
    steps_info.conditional_step = Step(
        name=conditional_step_name,
        command=build_step_command(files_to_create=[conditional_step_artifact, conditional_step_report_artifact],
                                   exit_code=conditional_step_exit_code),
        artifacts=conditional_step_artifact,
        report_artifacts=conditional_step_report_artifact)
    steps_info.is_conditional_step_passed = is_conditional_step_passed

    true_branch_step_name = "true_branch"
    true_branch_step_artifact = f"{true_branch_step_name}_artifact"
    true_branch_step_report_artifact = f"{true_branch_step_name}_report_artifact"
    steps_info.true_branch_step = Step(
        name=true_branch_step_name,
        command=build_step_command(files_to_create=[true_branch_step_artifact, true_branch_step_report_artifact],
                                   exit_code=0),
        artifacts=true_branch_step_artifact,
        report_artifacts=true_branch_step_report_artifact)

    false_branch_step_name = "false_branch"
    false_branch_step_artifact = f"{false_branch_step_name}_artifact"
    false_branch_step_report_artifact = f"{false_branch_step_name}_report_artifact"
    steps_info.false_branch_step = Step(
        name=false_branch_step_name,
        command=build_step_command(files_to_create=[false_branch_step_artifact, false_branch_step_report_artifact],
                                   exit_code=0),
        artifacts=false_branch_step_artifact,
        report_artifacts=false_branch_step_report_artifact)

    return steps_info


def build_step_command(files_to_create, exit_code):
    commands = []
    for f in files_to_create:
        commands.append(f"touch {f}")
    commands.append(f"exit {exit_code}")
    return ["bash", "-c", ";".join(commands)]


def write_config_file(tmpdir, conditional_steps_info):
    true_branch_step = f"Step(**{str(conditional_steps_info.true_branch_step)})" if conditional_steps_info.true_branch_step else "None"
    false_branch_step = f"Step(**{str(conditional_steps_info.false_branch_step)})" if conditional_steps_info.false_branch_step else "None"
    config_lines = [
        "from universum.configuration_support import Configuration, Step",
        f"true_branch_step = {true_branch_step}",
        f"false_branch_step = {false_branch_step}",
        f"conditional_step = Step(**{str(conditional_steps_info.conditional_step)})",

        # `true/false_branch_steps` should be Python objects from this script
        "conditional_step.is_conditional = True",
        "conditional_step.if_succeeded = true_branch_step",
        "conditional_step.if_failed = false_branch_step",

        "configs = Configuration([conditional_step])"
    ]
    config = "\n".join(config_lines)

    config_file = tmpdir.join("configs.py")
    config_file.write_text(config, "utf-8")

    return config_file


def check_conditional_step(tmpdir, capsys, steps_info):
    config_file = write_config_file(tmpdir, steps_info)

    artifacts_dir = tmpdir.join("artifacts")
    params = ["-vt", "none",
              "-fsd", str(tmpdir),
              "-ad", str(artifacts_dir),
              "--clean-build",
              "-o", "console"]
    params.extend(["-cfg", str(config_file)])

    return_code = __main__.main(params)
    assert return_code == 0

    captured = capsys.readouterr()
    conditional_succeeded_regexp = r"\] conditional.*Success.*\|   5\.2"
    assert re.search(conditional_succeeded_regexp, captured.out, re.DOTALL)

    artifacts_checker = ConditionalStepsArtifactChecker(artifacts_dir, steps_info)
    artifacts_checker.check_conditional_step_artifacts_present()
    artifacts_checker.check_executed_step_artifacts_present()
    artifacts_checker.check_not_executed_step_artifacts_absent()


def get_step_artifact(step):
    return step.artifacts if step else None


def get_step_report_artifact(step):
    return step.report_artifacts if step else None


class ConditionalStepsArtifactChecker:

    def __init__(self, artifacts_dir, steps_info):
        self.artifacts_dir = artifacts_dir
        self.is_conditional_step_passed = steps_info.is_conditional_step_passed
        self.conditional_step_artifact = get_step_artifact(steps_info.conditional_step)
        self.conditional_step_report_artifact = get_step_report_artifact(steps_info.conditional_step)
        self.true_branch_step_artifact = get_step_artifact(steps_info.true_branch_step)
        self.true_branch_step_report_artifact = get_step_report_artifact(steps_info.true_branch_step)
        self.false_branch_step_artifact = get_step_artifact(steps_info.false_branch_step)
        self.false_branch_step_report_artifact = get_step_report_artifact(steps_info.false_branch_step)

    def check_conditional_step_artifacts_present(self):
        assert os.path.exists(os.path.join(self.artifacts_dir, self.conditional_step_artifact))
        assert os.path.exists(os.path.join(self.artifacts_dir, self.conditional_step_report_artifact))

    def check_executed_step_artifacts_present(self):
        expected_artifact = self.true_branch_step_artifact if self.is_conditional_step_passed \
            else self.false_branch_step_artifact
        expected_report_artifact = self.true_branch_step_report_artifact if self.is_conditional_step_passed \
            else self.false_branch_step_report_artifact
        if expected_artifact:
            assert os.path.exists(os.path.join(self.artifacts_dir, expected_artifact))
        if expected_report_artifact:
            assert os.path.exists(os.path.join(self.artifacts_dir, expected_report_artifact))

    def check_not_executed_step_artifacts_absent(self):
        unexpected_artifact = self.false_branch_step_artifact if self.is_conditional_step_passed \
            else self.true_branch_step_artifact
        unexpected_report_artifact = self.false_branch_step_report_artifact if self.is_conditional_step_passed \
            else self.true_branch_step_report_artifact
        if unexpected_artifact:
            assert not os.path.exists(os.path.join(self.artifacts_dir, unexpected_artifact))
        if unexpected_report_artifact:
            assert not os.path.exists(os.path.join(self.artifacts_dir, unexpected_report_artifact))
