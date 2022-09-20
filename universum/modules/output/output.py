import sys
from typing import ClassVar

from .base_output import BaseOutput
from .github_output import GithubOutput
from .html_output import HtmlOutput
from .teamcity_output import TeamcityOutput
from .terminal_based_output import TerminalBasedOutput
from ...lib import utils
from ...lib.gravity import Module, Dependency

__all__ = [
    "HasOutput",
    "MinimalOut",
    "Output"
]


class Output(Module):
    teamcity_driver_factory = Dependency(TeamcityOutput)
    terminal_driver_factory = Dependency(TerminalBasedOutput)
    html_driver_factory = Dependency(HtmlOutput)
    github_driver_factory = Dependency(GithubOutput)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Output", "Log appearance parameters")
        parser.add_argument("--out-type", "-ot", dest="type", choices=["tc", "term", "jenkins", "github"],
                            help="Type of output to produce (tc - TeamCity, jenkins - Jenkins, term - terminal, "
                                 "github - Github Actions). TeamCity, Jenkins and Github Actions environments are "
                                 "detected automatically when launched on build agent.")
        # `universum` -> html_log == default
        # `universum -hl` -> html_log == const
        # `universum -hl custom` -> html_log == custom
        parser.add_argument("--html-log", "-hl", nargs="?", const=HtmlOutput.default_name, default=None,
                            help=f"Generate a self-contained user-friendly HTML log. "
                                 f"Pass a desired log name as a parameter to this option, or a default "
                                 f"'{HtmlOutput.default_name}' will be used.")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.driver: BaseOutput = \
            utils.create_driver(local_factory=self.terminal_driver_factory,
                                teamcity_factory=self.teamcity_driver_factory,
                                jenkins_factory=self.terminal_driver_factory,
                                github_factory=self.github_driver_factory,
                                env_type=self.settings.type)
        self.html_driver = self._create_html_driver()

    def log_execution_start(self, title: str, version: str) -> None:
        self.driver.log_execution_start(title, version)
        self.html_driver.log_execution_start(title, version)

    def log_execution_finish(self, title: str, version: str) -> None:
        self.driver.log_execution_finish(title, version)
        self.html_driver.log_execution_finish(title, version)

    def log(self, line: str) -> None:
        self.driver.log(line)
        self.html_driver.log(line)

    def log_error(self, description: str) -> None:
        self.driver.log_error(description)
        self.html_driver.log_error(description)

    def log_external_command(self, command: str) -> None:
        self.driver.log_external_command(command)
        self.html_driver.log_external_command(command)

    def log_stdout(self, line: str) -> None:
        self.driver.log_stdout(line)
        self.html_driver.log_stdout(line)

    def log_stderr(self, line: str) -> None:
        self.driver.log_stderr(line)
        self.html_driver.log_stderr(line)

    def open_block(self, number: str, name: str) -> None:
        self.driver.open_block(number, name)
        self.html_driver.open_block(number, name)

    def close_block(self, number: str, name: str, status: str) -> None:
        self.driver.close_block(number, name, status)
        self.html_driver.close_block(number, name, status)

    def log_skipped(self, message: str) -> None:
        self.driver.log_skipped(message)
        self.html_driver.log_skipped(message)

    def log_summary_step(self, step_title: str, has_children: bool, status: str) -> None:
        self.driver.log_summary_step(step_title, has_children, status)
        self.html_driver.log_summary_step(step_title, has_children, status)

    # TODO: pass build problem to the Report module
    def report_build_problem(self, problem: str) -> None:
        self.driver.report_build_problem(problem)

    def set_build_status(self, status: str) -> None:
        self.driver.set_build_status(status)

    def _create_html_driver(self):
        is_enabled = self.settings.html_log is not None
        html_driver = self.html_driver_factory(log_name=self.settings.html_log) if is_enabled else None
        handler = HtmlDriverHandler(html_driver)
        return handler


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
    def log_error(line: str) -> None:
        sys.stderr.write("Error: " + line)

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
