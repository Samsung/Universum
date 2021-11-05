import sys
import os
from types import TracebackType
from typing import ClassVar, Optional

from ...lib.gravity import Module, Dependency
from ...lib import utils
from .base_output import BaseOutput
from .terminal_based_output import TerminalBasedOutput
from .teamcity_output import TeamcityOutput
from .html_output import HtmlOutput

__all__ = [
    "HasOutput",
    "MinimalOut",
    "Output"
]


class Output(Module):
    teamcity_driver_factory = Dependency(TeamcityOutput)
    terminal_driver_factory = Dependency(TerminalBasedOutput)
    html_driver_factory = Dependency(HtmlOutput)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Output", "Log appearance parameters")
        parser.add_argument("--out-type", "-ot", dest="type", choices=["tc", "term", "jenkins"],
                            help="Type of output to produce (tc - TeamCity, jenkins - Jenkins, term - terminal). "
                                 "TeamCity and Jenkins environments are detected automatically when launched on build "
                                 "agent.")
        parser.add_argument("--html-log", "-hl", action="store_true", default=False,
                            help="Generate self-contained HTML log in artifacts directory")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.driver: BaseOutput = \
            utils.create_driver(local_factory=self.terminal_driver_factory,
                                teamcity_factory=self.teamcity_driver_factory,
                                jenkins_factory=self.terminal_driver_factory,
                                env_type=self.settings.type)
        self.html_driver = self._create_html_driver()

    def log(self, line: str) -> None:
        self.driver.log(line)
        self.html_driver.log(line)

    def log_external_command(self, command: str) -> None:
        self.driver.log_external_command(command)
        self.html_driver.log_external_command(command)

    def open_block(self, number: str, name: str) -> None:
        self.driver.open_block(number, name)
        self.html_driver.open_block(number, name)

    def close_block(self, number: str, name: str, status: str) -> None:
        self.driver.close_block(number, name, status)
        self.html_driver.close_block(number, name, status)

    def report_build_status(self, status: str) -> None:
        self.driver.change_status(status)
        self.html_driver.change_status(status)

    # TODO: pass build problem to the Report module
    def report_build_problem(self, problem: str) -> None:
        self.driver.report_error(problem)
        self.html_driver.report_error(problem)

    def report_skipped(self, message: str) -> None:
        self.driver.report_skipped(message)
        self.html_driver.report_skipped(message)

    def report_step(self, message: str, status: str) -> None:
        self.driver.report_step(message, status)
        self.html_driver.report_step(message, status)

    def log_exception(self, line: str) -> None:
        self.driver.log_exception(line)
        self.html_driver.log_exception(line)

    def log_stderr(self, line: str) -> None:
        self.driver.log_stderr(line)
        self.html_driver.log_stderr(line)

    def log_shell_output(self, line: str) -> None:
        self.driver.log_shell_output(line)
        self.html_driver.log_shell_output(line)

    def log_execution_start(self, title: str, version: str) -> None:
        self.driver.log_execution_start(title, version)
        self.html_driver.log_execution_start(title, version)

    def log_execution_finish(self, title: str, version: str) -> None:
        self.driver.log_execution_finish(title, version)
        self.html_driver.log_execution_finish(title, version)

    def _create_html_driver(self):
        html_driver = self.html_driver_factory() if self.settings.html_log else None
        return HtmlDriverHandler(html_driver)



class HasOutput(Module):
    out_factory: ClassVar = Dependency(Output)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.out: Output = self.out_factory()


class MinimalOut:
    def __init__(self, silent=False):
        self.silent = silent

    def log(self, line: str) -> None:
        if not self.silent:
            print(line)

    @staticmethod
    def report_build_problem(problem: str) -> None:
        pass

    @staticmethod
    def log_exception(exc: Exception) -> None:
        ex_traceback: Optional[TracebackType] = sys.exc_info()[2]
        sys.stderr.write("Unexpected error.\n" + utils.format_traceback(exc, ex_traceback))

    def log_execution_start(self, title, version):
        pass

    def log_execution_finish(self, title, version):
        pass


class HtmlDriverHandler:
    def __init__(self, driver):
        self.driver = driver

    def __getattr__(self, name):
        if self.driver:
            return getattr(self.driver, name)
        return lambda *args, **kwargs: None
