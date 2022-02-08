import locale
import sys

from .base_output import BaseOutput, TermColors

__all__ = [
    "TerminalBasedOutput"
]


def stdout(*args, **kwargs):
    sys.stdout.write(''.join(args))
    if not kwargs.get("no_enter", False):
        sys.stdout.write('\n')


class TerminalBasedOutput(BaseOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_level = 0
        self.unicode_acceptable = (locale.getpreferredencoding() == "UTF-8")

    def indent(self):
        for x in range(0, self.block_level):
            stdout("  " * x, " |   ", no_enter=True)

    def print_lines(self, *args):
        result = ''.join(args)
        lines = result.splitlines(False)
        for line in lines:
            self.indent()
            stdout(line)

    def open_block(self, num_str, name):
        self.indent()
        stdout(num_str, ' ', TermColors.blue, name, TermColors.reset)
        self.block_level += 1

    def close_block(self, num_str, name, status):
        self.block_level -= 1
        self.indent()
        if self.unicode_acceptable:
            block_end = " \u2514 "
        else:
            block_end = " | "

        if status == "Failed":
            stdout(self.block_level * "  ", block_end, TermColors.red, "[Failed]", TermColors.reset)
        else:
            stdout(self.block_level * "  ", block_end, TermColors.green, "[Success]", TermColors.reset)
        self.indent()
        stdout()

    def report_error(self, description):
        pass

    def report_skipped(self, message):
        self.print_lines(TermColors.dark_cyan, message, TermColors.reset)

    def report_step(self, message, status):
        color = TermColors.red
        if status.lower() == "success":
            color = TermColors.green

        if message.endswith(status):
            message = message[:-len(status)]
            message += color + status + TermColors.reset
        self.log(message)

    def change_status(self, message):
        pass

    def log_exception(self, line):
        self.print_lines(TermColors.dark_red, "Error: ", TermColors.reset, line)

    def log_stderr(self, line):
        self.print_lines(TermColors.dark_yellow, "stderr: ", TermColors.reset, line)

    def log(self, line):
        self.print_lines("==> ", line)

    def log_external_command(self, command):
        self.print_lines("$ ", command)

    def log_shell_output(self, line):
        self.print_lines(line)
