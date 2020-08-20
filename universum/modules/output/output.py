from typing import Type

from ...lib.gravity import Module, Dependency
from ...lib import utils
from .terminal_based_output import TerminalBasedOutput
from .teamcity_output import TeamcityOutput

__all__ = [
    "HasOutput"
]


class Output(Module):
    teamcity_driver_factory = Dependency(TeamcityOutput)
    terminal_driver_factory = Dependency(TerminalBasedOutput)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Output", "Log appearance parameters")
        parser.add_argument("--out-type", "-ot", dest="type", choices=["tc", "term", "jenkins"],
                            help="Type of output to produce (tc - TeamCity, jenkins - Jenkins, term - terminal). "
                                 "TeamCity environment is detected automatically when launched on build agent.")

    def __init__(self, *args, **kwargs):
        super(Output, self).__init__(*args, **kwargs)
        self.driver = utils.create_driver(local_factory=self.terminal_driver_factory,
                                          teamcity_factory=self.teamcity_driver_factory,
                                          jenkins_factory=self.terminal_driver_factory,
                                          env_type=self.settings.type)

    def log(self, line):
        self.driver.log(line)

    def log_external_command(self, command):
        self.driver.log_external_command(command)

    def open_block(self, number, name):
        self.driver.open_block(number, name)

    def close_block(self, number, name, status):
        self.driver.close_block(number, name, status)

    def report_build_status(self, status):
        self.driver.change_status(status)

    # TODO: pass build problem to the Report module
    def report_build_problem(self, problem):
        self.driver.report_error(problem)

    def report_skipped(self, message):
        self.driver.report_skipped(message)

    def report_step(self, message, status):
        self.driver.report_step(message, status)

    def log_exception(self, line):
        self.driver.log_exception(line)

    def log_stderr(self, line):
        self.driver.log_stderr(line)

    def log_shell_output(self, line):
        self.driver.log_shell_output(line)


class HasOutput(Module):
    out_factory: Dependency[Output] = Dependency(Output)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.out: Output = self.out_factory()
