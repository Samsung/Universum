import re
import pytest
import inspect

from universum import __main__


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

    config = inspect.cleandoc(f'''
        from universum.configuration_support import Configuration, Step

        true_branch_step = Step(name='{true_branch_step_name}', command=['touch', '{true_branch_step_name}'],
                                artifacts='{true_branch_step_name}')
        false_branch_step = Step(name='{false_branch_step_name}', command=['touch', '{false_branch_step_name}'])
        conditional_step = Configuration([dict(name='conditional',
            command=['bash', '-c', 'exit {conditional_step_exit_code}'],
            if_succeeded=true_branch_step, if_failed=false_branch_step)])

        configs = conditional_step
    ''')

    config_file = tmpdir.join("configs.py")
    config_file.write_text(config, "utf-8")

    return config_file


def check_conditional_step(tmpdir, capsys, config_file, conditional_step_passed):
    params = ["-vt", "none",
              "-fsd", str(tmpdir),
              "--clean-build",
              "-o", "console"]
    params.extend(["-cfg", str(config_file)])

    return_code = __main__.main(params)
    assert return_code == 0

    captured = capsys.readouterr()
    print(captured.out)
    conditional_succeeded_regexp = r"conditional.*Success.*\|   5\.2"
    assert re.search(conditional_succeeded_regexp, captured.out, re.DOTALL)

    expected_log = true_branch_step_name if conditional_step_passed else false_branch_step_name
    unexpected_log = false_branch_step_name if conditional_step_passed else true_branch_step_name
    assert expected_log in captured.out
    assert not unexpected_log in captured
