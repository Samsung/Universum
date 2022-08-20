from .terminal_based_output import TerminalBasedOutput

__all__ = [
    "GithubOutput"
]


class GithubOutput(TerminalBasedOutput):
    """
    GitHub Actions manual: https://docs.github.com/en/actions
    GitHub doesn't support nested grouping (https://github.com/actions/runner/issues/802)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._block_opened = False

    def _print_lines(self, *args, **kwargs):
        prefix = kwargs.setdefault("prefix", "")
        result = "".join(args)
        lines = result.splitlines(False)
        for line in lines:
            self._stdout(f"{prefix}{line}")

    def log_error(self, description):
        self._print_lines(description, prefix="::error::")

    def log_stderr(self, line):
        self._print_lines("stderr: ", line, prefix="::warning::")

    def open_block(self, num_str, name):
        if self._block_opened:
            self._print_lines("::endgroup::")

        self._print_lines(f"::group::{num_str} {name}")
        self._block_opened = True

    def close_block(self, num_str, name, status):
        if self._block_opened:
            self._block_opened = False
            self._print_lines("::endgroup::")

        if status == "Failed":
            self._print_lines(f"::error::{num_str} {name} - Failed")

    def log_skipped(self, message):
        self._print_lines(message, prefix="::warning::")
