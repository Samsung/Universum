# -*- coding: UTF-8 -*-

import sys

from .base_output import BaseOutput

__all__ = [
    "JenkinsOutput",
    "LocalOutput",
    "TerminalBasedOutput"
]


class Colors(object):
    red = "\033[1;31m"
    dark_red = "\033[0;31m"
    green = "\033[1;32m"
    blue = "\033[1;34m"
    dark_cyan = "\033[0;36m"
    dark_yellow = "\033[0;33m"
    reset = "\033[00m"


def stdout(*args, **kwargs):
    sys.stdout.write(''.join(args))
    if not kwargs.get("no_enter", False):
        sys.stdout.write('\n')


class TerminalBasedOutput(BaseOutput):
    line_start = None
    block_start = None
    block_end = None

    def __init__(self, *args, **kwargs):
        super(TerminalBasedOutput, self).__init__(*args, **kwargs)
        if None in [self.line_start, self.block_start, self.block_end]:
            raise NotImplementedError()
        self.block_level = 0

    def indent(self):
        for x in range(0, self.block_level):
            stdout("  " * x, self.line_start, no_enter=True)

    def print_lines(self, *args):
        result = ''.join(args)
        lines = result.split("\n")
        for line in lines:
            self.indent()
            stdout(line)

    def open_block(self, num_str, name):
        self.indent()
        stdout(self.block_start, num_str, ' ', Colors.blue, name, Colors.reset)
        self.block_level += 1

    def close_block(self, num_str, name, status):
        self.block_level -= 1
        self.indent()

        if status == "Failed":
            stdout(self.block_level * "  ", self.block_end, Colors.red, "[Failed]", Colors.reset)
        else:
            stdout(self.block_level * "  ", self.block_end, Colors.green, "[Success]", Colors.reset)
        self.indent()
        stdout()

    def report_error(self, description):
        pass

    def report_skipped(self, message):
        self.print_lines(Colors.dark_cyan, message, Colors.reset)

    def report_step(self, message, status):
        color = Colors.red
        if status.lower() == "success":
            color = Colors.green

        if message.endswith(status):
            message = message[:-len(status)]
            message += color + status + Colors.reset
        self.log(message)

    def change_status(self, message):
        pass

    def log_exception(self, line):
        self.print_lines(Colors.dark_red, "Error: ", Colors.reset, line)

    def log_stderr(self, line):
        self.print_lines(Colors.dark_yellow, "stderr: ", Colors.reset, line)

    def log(self, line):
        self.print_lines("==> ", line)

    def log_external_command(self, command):
        self.print_lines("$ ", command)

    def log_shell_output(self, line):
        self.print_lines(line)


class LocalOutput(TerminalBasedOutput):
    line_start = u" |   "
    block_start = u""
    block_end = u" \u2514 "


JenkinsOutput = LocalOutput
