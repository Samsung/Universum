# -*- coding: UTF-8 -*-

import copy
import os
import os.path
import sys
import json
import sh

from . import configuration_support, utils, artifact_collector
from .ci_exception import CiException, CriticalCiException, StepException
from .gravity import Module, Dependency
from .module_arguments import IncorrectParameterError
from .output import needs_output
from .utils import make_block
from .reporter import Reporter

__all__ = [
    "Launcher"
]


def make_command(name):
    try:
        return sh.Command(name)
    except sh.CommandNotFound:
        text = "No such file or command as '" + name + "'"
        raise CiException(text)


def check_if_env_set(variations):
    if "if_env_set" in variations:
        variables = variations["if_env_set"].split("&")
        for var in variables:
            if var.strip():
                if "==" in var.strip():
                    comparison = var.strip().split("==")
                    if len(comparison) != 2:
                        raise CriticalCiException("Comparison '" + var.strip() + "' cannot be parsed")
                    if not os.getenv(comparison[0].strip()):
                        return False
                    if os.getenv(comparison[0].strip()) != comparison[1].strip():
                        return False
                else:
                    if not os.getenv(var.strip()):
                        return False
                    if os.getenv(var.strip()) not in ["True", "true", "Yes", "yes", "Y", "y"]:
                        return False
    return True


def finalize_execution(cmd, log):
    try:
        text = ""
        try:
            cmd.wait()
        except Exception as e:
            if isinstance(e, sh.ErrorReturnCode):
                text = "Module sh got exit code " + unicode(e.exit_code) + "\n"
                if e.stderr:
                    text += utils.trim_and_convert_to_unicode(e.stderr) + "\n"
            else:
                text = unicode(e) + "\n"
        stderr = '\n'.join(log.error_lines)
        if text:
            log.report_fail(text + stderr)
            raise StepException()
        else:
            if stderr:
                log.report_warning(stderr)
            log.report_success()

    finally:
        log.end_log()


class LogWriter(object):
    # TODO: change to non-singleton module and get all dependencies by ourselves
    def __init__(self, out, artifacts, reporter, output_type, step_name, background=False):
        self.out = out
        self.reporter = reporter
        self.background = background
        self.step_name = step_name
        self.error_lines = []

        if self.background:
            output_type = "file"

        if output_type == "file":
            self.file = artifacts.create_text_file(step_name + "_log.txt")
            self.out.log("Execution log is redirected to file")
        else:
            self.file = None

    def print_cmd(self, line):
        line = utils.trim_and_convert_to_unicode(line)

        self.out.log_external_command(line)
        if self.file:
            self.file.write("$ " + line + "\n")

    def handle_stdout(self, line=u""):
        line = utils.trim_and_convert_to_unicode(line)

        if self.file:
            self.file.write(line + "\n")
        else:
            self.out.log_shell_output(line)

    def handle_stderr(self, line):
        line = utils.trim_and_convert_to_unicode(line)
        if self.file:
            self.file.write("stderr: " + line + "\n")
            self.error_lines.append(line)
        else:
            self.out.log_stderr(line)

    def report_warning(self, line):
        self.out.log_stderr(line)

    def report_fail(self, line):
        line = utils.trim_and_convert_to_unicode(line)

        if self.file:
            self.file.write(line + "\n")
        self.out.fail_current_block(line)
        self.reporter.report_build_step(self.step_name, False)

    def report_success(self):
        self.reporter.report_build_step(self.step_name, True)

    def end_log(self):
        self.handle_stdout()
        if self.file:
            self.file.close()


class LogWriterCodeReport(LogWriter):
    def __init__(self, out, artifacts, reporter, step_name, background):
        super(LogWriterCodeReport, self).__init__(out, artifacts, reporter, "file", step_name, background)
        self.collect = ''

    def report_comments(self, report):
        for result in report:
            text = result["symbol"] + ": " + result["message"]
            self.reporter.code_report(result["path"], {"message": text, "line": result["line"]})

    def handle_stdout(self, line=u""):
        self.collect += utils.trim_and_convert_to_unicode(line)

    def end_log(self):
        report = []
        try:
            report = json.loads(self.collect)
        except (ValueError, TypeError) as e:
            # skip error if self.collect is empty or consists of spaces
            if e.message != "No JSON object could be decoded":
                self.out.log_stderr(e.message)

        self.file.write(json.dumps(report, indent=4))
        self.report_comments(report)
        self.out.log_shell_output("Found " + str(len(report)) + " issues.")


@needs_output
class Launcher(Module):
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Configuration execution",
                                                     "External command launching and reporting parameters")

        parser.add_argument("--launcher-output", "-lo", dest="output", choices=["console", "file"],
                            help="Define whether to print build logs to console or store to files. "
                                 "Log file names are generated based on the names of build steps. "
                                 "Possible values: 'console', 'file'. By default, logs are printed to console "
                                 "when the build is launched on TeamCity agent")

        parser.add_argument("--launcher-config-path", "-lcp", dest="config_path", metavar="CONFIG_PATH",
                            help="Project configs.py file location. Mandatory parameter")

    def __init__(self, settings, project_root):
        self.project_root = project_root
        self.configs_current_number = 0
        self.configs_total_count = 0
        self.settings = settings
        self.background_processes = []
        self.source_project_configs = None
        self.project_configs = None

        if settings.output is None:
            if utils.detect_environment() != "tc":
                settings.output = "file"
            else:
                settings.output = "console"

        if getattr(self.settings, "config_path") is None:
            raise IncorrectParameterError(
                "Required option CONFIG_PATH (or '--launcher-config-path', or '-lcp') is missing.")

        self.artifacts = self.artifacts_factory()
        self.reporter = self.reporter_factory()

    @make_block("Processing project configs")
    def process_project_configs(self):

        config_path = utils.parse_path(self.settings.config_path, self.project_root)
        configuration_support.set_project_root(self.project_root)
        config_globals = {}
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        sys.path.append(os.path.join(os.path.dirname(config_path)))

        try:
            execfile(config_path, config_globals)
            self.source_project_configs = config_globals["configs"]
            self.project_configs = self.source_project_configs.filter(check_if_env_set)
            self.configs_total_count = sum(1 for _ in self.project_configs.all())

        except IOError as e:
            text = unicode(e) + "\nPossible reasons of this error:\n" + \
                   " * There is no file named 'configs.py' in project repository\n" + \
                   " * Config path, passed to the script ('" + self.settings.config_path + \
                   "'), does not lead to actual 'configs.py' location\n" + \
                   " * Some problems occurred while downloading or copying the repository"
            raise CriticalCiException(text)
        except KeyError as e:
            text = "KeyError: " + unicode(e) + \
                   "\nPossible reason of this error: variable 'configs' is not defined in 'configs.py'"
            raise CriticalCiException(text)
        except Exception as e:
            ex_traceback = sys.exc_info()[2]
            text = "Exception while processing 'configs.py'\n" + utils.format_traceback(e, ex_traceback) + \
                   "\nPlease copy 'configs.py' script to the CI scripts folder and run it " + \
                   "to make sure no exceptions occur in that case."
            raise CriticalCiException(text)
        return self.project_configs

    def run_cmd(self, name, step_name, working_directory, background, code_report, *args, **kwargs):
        try:
            try:
                cmd = make_command(name)
            except CiException:
                if working_directory is None:
                    raise
                name = os.path.abspath(os.path.join(working_directory, name))
                cmd = make_command(name)
        except CiException as ex:
            self.out.fail_current_block(unicode(ex))
            raise StepException()
        if code_report:
            log_writer = LogWriterCodeReport(self.out, self.artifacts, self.reporter, step_name, background)
        else:
            log_writer = LogWriter(self.out, self.artifacts, self.reporter, self.settings.output, step_name, background)
        ret = cmd(*args, _iter=True, _cwd=working_directory, _bg_exc=False, _bg=background,
                  _out=log_writer.handle_stdout, _err=log_writer.handle_stderr, **kwargs)
        log_writer.print_cmd(ret.ran)

        if background:
            self.background_processes.append({'cmd': ret, 'log': log_writer})
            self.out.log("Will continue in background")
        else:
            finalize_execution(ret, log_writer)

    def execute_configuration(self, item):
        try:
            command_path = utils.strip_path_start(item["command"][0])
            working_directory = utils.parse_path(utils.strip_path_start(item.get("directory", "").rstrip("/")),
                                                 self.project_root)
            self.run_cmd(command_path, item.get("name", ''), working_directory, item.get("background", False),
                         item.get("code_report", False), *(item["command"][1:]))
        except KeyError as e:
            if e.message == "command":
                self.out.log("No 'command' found. Nothing to execute")
            else:
                raise

    def execute_steps_recursively(self, parent, variations):
        if parent is None:
            parent = dict()

        child_step_failed = False
        for obj_a in variations:
            try:
                item = configuration_support.combine(parent, copy.deepcopy(obj_a))

                if "children" in obj_a:
                    # Here pass_errors=True, because any exception outside executing build step
                    # is not step-related and should stop script executing

                    self.out.run_in_block(self.execute_steps_recursively, item.get("name", ''), True, item,
                                          obj_a["children"])
                else:
                    self.configs_current_number += 1
                    step_name = " [ " + unicode(self.configs_current_number) + "/" + \
                                unicode(self.configs_total_count) + " ] " + item.get("name", '')
                    # Here pass_errors=False, because any exception while executing build step
                    # can be step-related and may not affect other steps

                    self.out.run_in_block(self.execute_configuration, step_name, False, item)
            except StepException:
                child_step_failed = True
                if obj_a.get("critical", False):
                    break
        if child_step_failed:
            raise StepException

    @make_block("Reporting background steps")
    def report_background_steps(self):
        for process in self.background_processes:
            self.out.run_in_block(finalize_execution, process['log'].step_name, False, **process)

    def launch_project(self):
        try:
            self.out.run_in_block(self.execute_steps_recursively, "Executing build steps", True,
                                  None, self.project_configs)
            if self.background_processes:
                self.report_background_steps()
        except StepException:
            pass
            # StepException only stops build step execution,
            # not affecting other Universum functions, e.g. artifact collecting or finalizing
