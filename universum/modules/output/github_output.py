from .terminal_based_output import TerminalBasedOutput

__all__ = [
    "GithubOutput"
]


class GithubOutput(TerminalBasedOutput):
    """
    Github Actions manual: https://docs.github.com/en/actions
    GitHub doesn't support nested grouping (https://github.com/actions/runner/issues/802)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._block_opened = False

    def print_lines(self, *args, **kwargs):
        prefix = kwargs.setdefault("prefix", "")
        result = "".join(args)
        lines = result.splitlines(False)
        for line in lines:
            self.stdout(f"{prefix}{line}")

    def open_block(self, num_str, name):
        if self._block_opened:
            self.print_lines("::endgroup::")

        self.print_lines(f"::group::{num_str} {name}")
        self._block_opened = True

    def close_block(self, num_str, name, status):
        if self._block_opened:
            self._block_opened = False
            self.print_lines("::endgroup::")

        if status == "Failed":
            self.print_lines(f"::error::{num_str} {name} - Failed")

    def report_skipped(self, message):
        self.print_lines(message, prefix="::warning::")

    def log_exception(self, line):
        self.print_lines(line, prefix="::error::")

    def log_stderr(self, line):
        self.print_lines("stderr: ", line, prefix="::warning::")
