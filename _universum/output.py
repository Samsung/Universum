# -*- coding: UTF-8 -*-

from . import jenkins_driver, teamcity_driver, local_driver, utils
from .gravity import Module, Dependency
from .ci_exception import CriticalCiException, SilentAbortException, CriticalStepException

__all__ = [
    "Output",
    "needs_output"
]


class Block(object):
    def __init__(self, name):
        self.name = name
        self.status = "Success"
        self.child_number = 1


def needs_output(klass):
    klass.out_factory = Dependency("Output")
    original_init = klass.__init__

    def new_init(self, *args, **kwargs):
        self.out = self.out_factory()
        original_init(self, *args, **kwargs)

    klass.__init__ = new_init

    return klass


class Output(Module):
    teamcity_driver_factory = Dependency(teamcity_driver.TeamCityOutput)
    local_driver_factory = Dependency(local_driver.LocalOutput)
    jenkins_driver_factory = Dependency(jenkins_driver.JenkinsOutput)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Output", "Log appearance parameters")
        parser.add_argument("--out-type", "-ot", dest="type", choices=["tc", "term", "jenkins"],
                            help="Type of output to produce (tc - TeamCity, jenkins - Jenkins, term - terminal). "
                                 "TeamCity environment is detected automatically when launched on build agent.")

    def __init__(self, settings):
        self.top_block_number = 1
        self.blocks = []

        self.driver = utils.create_diver(local_factory=self.local_driver_factory,
                                         teamcity_factory=self.teamcity_driver_factory,
                                         jenkins_factory=self.jenkins_driver_factory,
                                         default=settings.type)

    def log(self, line):
        self.driver.log(line)

    def log_external_command(self, command):
        self.driver.log_external_command(command)

    def get_block_num_str(self):
        num_str = unicode(self.top_block_number) + "."
        for block in self.blocks:
            num_str += unicode(block.child_number) + "."
        return num_str

    def open_block(self, name):
        self.driver.open_block(self.get_block_num_str(), name)
        self.blocks.append(Block(name))

    def close_block(self):
        block = self.blocks.pop()
        if block.status == "Failed":
            self.report_build_problem(block.name + " " + block.status)

        self.driver.close_block(self.get_block_num_str(), block.name, block.status)

        if not self.blocks:
            self.top_block_number += 1
        else:
            self.blocks[-1].child_number += 1

    def fail_current_block(self, error=None):
        if error:
            self.log_exception(error)
        self.blocks[-1].status = "Failed"

    def log_exception(self, line):
        self.driver.log_exception(line)

    def log_stderr(self, line):
        self.driver.log_stderr(line)

    def log_shell_output(self, line):
        self.driver.log_shell_output(line)

    # TODO: pass build problem to the Report module
    def report_build_problem(self, problem):
        self.driver.report_error(problem)

    def report_build_status(self, status):
        self.driver.change_status(status)

    # The exact block will be reported as failed only if pass_errors is False
    # Otherwise the exception will be passed to the higher level function and handled there
    def run_in_block(self, operation, block_name, pass_errors, *args, **kwargs):
        result = None
        self.open_block(block_name)
        try:
            result = operation(*args, **kwargs)
        except SilentAbortException:
            raise
        except CriticalStepException as ex:
            if ex.message:
                self.fail_current_block(unicode(ex))
            raise CriticalStepException()
        except CriticalCiException as e:
            self.fail_current_block(unicode(e))
            raise SilentAbortException()
        except Exception as e:
            if pass_errors is True:
                raise
            else:
                self.fail_current_block(unicode(e))
        finally:
            self.close_block()
        return result
