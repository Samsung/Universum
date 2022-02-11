from .base_output import BaseOutput

__all__ = [
    "GithubOutput"
]


class GithubOutput(BaseOutput):
    """
    GitHub doesn't support nested grouping
    See: https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#grouping-log-lines
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._block_opened = False

    def open_block(self, num_str, name):
        if self._block_opened:
            print("::endgroup::")

        print(f"::group::{num_str} {name}")
        self._block_opened = True

    def close_block(self, num_str, name, status):
        if self._block_opened:
            self._block_opened = False
            print("::endgroup::")

        if status == "Failed":
            print(f'::error::{num_str} {name} - Failed')

    def report_error(self, description):
        pass

    def report_skipped(self, message):
        lines = message.splitlines(False)
        for single_line in lines:
            print(f"::warning::{single_line}")

    def change_status(self, message):
        pass

    def log_exception(self, line):
        lines = line.splitlines(False)
        for single_line in lines:
            print(f"::error::{single_line}")

    def log_stderr(self, line):
        lines = line.splitlines(False)
        for single_line in lines:
            print(f"::warning::stderr: {single_line}")

    def log(self, line):
        print("==>", line)

    def log_external_command(self, command):
        print("$", command)

    def log_shell_output(self, line):
        print(line)
