import re
import os
import inspect

from universum import __main__
from universum.configuration_support import Step, Configuration


conditional_step_name = "conditional"
true_branch_step_name = "true_branch"
false_branch_step_name = "false_branch"


def test_conditional_true_branch(tmpdir, capsys):
    check_conditional_step_success(tmpdir, capsys, conditional_step_passed=True)


def test_conditional_false_branch(tmpdir, capsys):
    check_conditional_step_success(tmpdir, capsys, conditional_step_passed=False)


def check_conditional_step_success(tmpdir, capsys, conditional_step_passed):
    config_file = build_config_file(tmpdir, conditional_step_passed)
    check_conditional_step(tmpdir, capsys, config_file, conditional_step_passed)


def build_config_file(tmpdir, conditional_step_passed):
    conditional_step_exit_code = 0 if conditional_step_passed else 1

    true_branch_step = Step(
        name=true_branch_step_name,
        command=['touch', true_branch_step_name],
        artifacts=true_branch_step_name)

    false_branch_step = Step(
        name=false_branch_step_name,
        command=['touch', false_branch_step_name],
        artifacts=false_branch_step_name)

    conditional_step = Step(
        name=conditional_step_name,
        command=['bash', '-c', f'touch {conditional_step_name}; exit {conditional_step_exit_code}'],
        artifacts=conditional_step_name)

    config = inspect.cleandoc(f'''
        from universum.configuration_support import Configuration, Step

        true_branch_step = Step(**{str(true_branch_step)})
        false_branch_step = Step(**{str(false_branch_step)})
        conditional_step = Step(**{str(conditional_step)})
        
        # `true/false_branch_steps` should be Python objects from this script
        conditional_step.is_conditional = True
        conditional_step.if_succeeded = true_branch_step
        conditional_step.if_failed = false_branch_step

        configs = Configuration([conditional_step])
    ''')

    config_file = tmpdir.join("configs.py")
    config_file.write_text(config, "utf-8")

    return config_file


def check_conditional_step(tmpdir, capsys, config_file, conditional_step_passed):
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

    assert os.path.exists(os.path.join(artifacts_dir, conditional_step_name))
    expected_file = true_branch_step_name if conditional_step_passed else false_branch_step_name
    unexpected_file = false_branch_step_name if conditional_step_passed else true_branch_step_name
    assert os.path.exists(os.path.join(artifacts_dir, expected_file))
    assert not os.path.exists(os.path.join(artifacts_dir, unexpected_file))

