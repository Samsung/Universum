from .terminal_based_output import TerminalBasedOutput, stdout

__all__ = [
    "GithubOutput"
]


class GithubOutput(TerminalBasedOutput):
    """
    GitHub doesn't support nested grouping
    See: https://github.com/actions/runner/issues/802
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._block_opened = False
        self.prefix = None

    def print_lines(self, *args):
        result = ''.join(args)
        lines = result.splitlines(False)
        for line in lines:
            if self.prefix:
                line = f"{self.prefix}{line}"
            stdout(line)

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
            self.print_lines(f'::error::{num_str} {name} - Failed')

    def report_skipped(self, message):
        try:
            self.prefix = "::warning::"
            super().report_skipped(message)
        finally:
            self.prefix = None

    def log_exception(self, line):
        try:
            self.prefix = "::error::"
            super().log_exception(line)
        finally:
            self.prefix = None

    def log_stderr(self, line):
        try:
            self.prefix = "::warning::"
            super().log_stderr(line)
        finally:
            self.prefix = None
