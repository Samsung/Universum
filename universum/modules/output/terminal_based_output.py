import locale
import sys
from typing import List

from .base_output import BaseOutput

__all__ = [
    "TerminalBasedOutput"
]


class Colors:
    red = "\033[1;31m"
    dark_red = "\033[0;31m"
    green = "\033[1;32m"
    blue = "\033[1;34m"
    dark_cyan = "\033[0;36m"
    dark_yellow = "\033[0;33m"
    reset = "\033[00m"


class TerminalBasedOutput(BaseOutput):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.block_level = 0
        self.unicode_acceptable = (locale.getpreferredencoding() == "UTF-8")  # pylint: disable = superfluous-parens

    @staticmethod
    def _stdout(*args, **kwargs) -> None:
        sys.stdout.write(''.join(args))
        if not kwargs.get("no_enter", False):
            sys.stdout.write('\n')

    def _indent(self) -> None:
        for x in range(0, self.block_level):
            self._stdout("  " * x, " |   ", no_enter=True)

    def _print_lines(self, *args, **kwargs) -> None:
        result: str = ''.join(args)
        lines: List[str] = result.splitlines(False)
        for line in lines:
            self._indent()
            self._stdout(line)

    def log(self, line: str) -> None:
        self._print_lines("==> ", line)

    def log_error(self, description: str) -> None:
        self._print_lines(Colors.dark_red, "Error: ", Colors.reset, description)

    def log_external_command(self, command: str) -> None:
        self._print_lines("$ ", command)

    def log_stdout(self, line: str) -> None:
        self._print_lines(line)

    def log_stderr(self, line: str) -> None:
        self._print_lines(Colors.dark_yellow, "stderr: ", Colors.reset, line)

    def open_block(self, num_str: str, name: str) -> None:
        self._indent()
        self._stdout(num_str, ' ', Colors.blue, name, Colors.reset)
        self.block_level += 1

    def close_block(self, num_str: str, name: str, status: str) -> None:
        self.block_level -= 1
        self._indent()
        if self.unicode_acceptable:
            block_end = " \u2514 "
        else:
            block_end = " | "

        if status == "Failed":
            self._stdout(self.block_level * "  ", block_end, Colors.red, "[Failed]", Colors.reset)
        else:
            self._stdout(self.block_level * "  ", block_end, Colors.green, "[Success]", Colors.reset)
        self._indent()
        self._stdout()

    def log_skipped(self, message: str) -> None:
        self._print_lines(Colors.dark_cyan, message, Colors.reset)

    def log_summary_step(self, step_title: str, has_children: bool, status: str) -> None:
        color = Colors.red
        if status.lower() == "success":
            color = Colors.green

        if not has_children:
            step_title += " - " + color + status + Colors.reset

        self.log(step_title)

    def report_build_problem(self, description: str) -> None:
        pass

    def set_build_status(self, status: str) -> None:
        pass
