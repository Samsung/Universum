# -*- coding: UTF-8 -*-

import os
import re
import sys
import json
import sh

from . import configuration_support, utils, artifact_collector, automation_server, reporter
from .ci_exception import CiException, CriticalCiException, StepException
from .gravity import Module, Dependency
from .module_arguments import IncorrectParameterError
from .output import needs_output
from .structure_handler import needs_structure
from .utils import make_block

__all__ = [
    "Launcher",
    "check_if_env_set"
]


def make_command(name):
    try:
        return sh.Command(name)
    except sh.CommandNotFound:
        text = "No such file or command as '" + name + "'"
        raise CiException(text)


def check_if_env_set(configuration):
    """
    Predicate function for :func:`_universum.configuration_support.Variations.filter`,
    used to decide whether this particular configuration should be executed in this
    particular environment. For more information see :ref:`filtering`

    >>> from _universum.configuration_support import Variations
    >>> c = Variations([dict(if_env_set="MY_VAR != some value")])
    >>> check_if_env_set(c[0])
    True

    >>> c = Variations([dict(if_env_set="MY_VAR != some value && OTHER_VAR")])
    >>> check_if_env_set(c[0])
    False

    >>> c = Variations([dict(if_env_set="MY_VAR == some value")])
    >>> os.environ["MY_VAR"] = "some value"
    >>> check_if_env_set(c[0])
    True

    :param configuration: :class:`~_universum.configuration_support.Variations`
           object containing one leaf configuration
    :return: True if environment satisfies described requirements; False otherwise
    """

    if "if_env_set" in configuration:
        variables = configuration["if_env_set"].split("&&")
        for var in variables:
            if var.strip():
                match = re.match(r"\s*([A-Za-z_]\w*)\s*(!=|==)\s*(.*?)\s*$", var)

                # With no operator 'match' is None
                # In this case variable should be obligatory set to any positive value
                if not match:
                    if not os.getenv(var.strip()):
                        return False
                    if os.getenv(var.strip()) not in ["True", "true", "Yes", "yes", "Y", "y"]:
                        return False
                    continue

                name, operator, value = match.groups()
                # In "==" case variable should be obligatory set to 'value'
                if operator == "==":
                    if os.getenv(name) is None:
                        return False
                    if os.getenv(name) != value:
                        return False

                # In "!=" case variable can be unset or set to any value not matching 'value'
                elif os.getenv(name) is not None:
                    if os.getenv(name) == value:
                        return False
    return True


def finalize_execution(cmd, log, pass_tag, fail_tag):
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
            if fail_tag:
                log.add_tag(fail_tag)
            raise StepException()
        else:
            if stderr:
                log.report_warning(stderr)
            if pass_tag:
                log.add_tag(pass_tag)
    finally:
        log.end_log()


class LogWriter(object):
    # TODO: change to non-singleton module and get all dependencies by ourselves
    def __init__(self, out, structure, artifacts, reporter, server, output_type, step_name, background=False):
        self.out = out
        self.structure = structure
        self.artifacts = artifacts
        self.reporter = reporter
        self.background = background
        self.step_name = step_name
        self.error_lines = []
        self.server = server

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
        self.error_lines.append(line)
        if self.file:
            self.file.write("stderr: " + line + "\n")
        else:
            self.out.log_stderr(line)

    def report_warning(self, line):
        self.out.log_stderr(line)

    def report_fail(self, line):
        line = utils.trim_and_convert_to_unicode(line)

        if self.file:
            self.file.write(line + "\n")
        self.structure.fail_current_block(line)

    def add_tag(self, tag):
        request = self.server.add_build_tag(tag)
        if request.status_code != 200:
            self.out.log_stderr(request.text)
        else:
            self.out.log("Tag '" + tag + "' added to build.")

    def end_log(self):
        self.handle_stdout()
        if self.file:
            self.file.close()


class LogWriterCodeReport(LogWriter):
    def __init__(self, report_file, *args, **kwargs):
        super(LogWriterCodeReport, self).__init__(*args, **kwargs)
        self.report_file = report_file

    def report_comments(self, report):
        for result in report:
            text = result["symbol"] + ": " + result["message"]
            self.reporter.code_report(result["path"], {"message": text, "line": result["line"]})

    def end_log(self):
        if os.path.exists(self.report_file):
            with open(self.report_file, "r") as f:
                report = json.loads(f.read())

            json_file = self.artifacts.create_text_file("Static_analysis_report.json")
            json_file.write(json.dumps(report, indent=4))

            self.report_comments(report)
            if report:
                text = unicode(len(report)) + " issues"
                self.error_lines.append(text)
                self.structure.fail_current_block("Found " + text)
                self.out.report_build_status(self.step_name + ": " + text)
        if not self.error_lines:  # e.g. required module is not installed (pylint, load-plugins for pylintrc)
            self.out.log("Issues not found.")


@needs_output
@needs_structure
class Launcher(Module):
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)
    reporter_factory = Dependency(reporter.Reporter)
    server_factory = Dependency(automation_server.AutomationServer)

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

    def __init__(self, project_root):
        self.project_root = project_root
        self.background_processes = []
        self.source_project_configs = None
        self.project_configs = None

        if self.settings.output is None:
            if utils.detect_environment() != "tc":
                self.settings.output = "file"
            else:
                self.settings.output = "console"

        if getattr(self.settings, "config_path") is None:
            raise IncorrectParameterError(
                "Required option CONFIG_PATH (or '--launcher-config-path', or '-lcp') is missing.")

        self.artifacts = self.artifacts_factory()
        self.reporter = self.reporter_factory()
        self.server = self.server_factory()

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
            dump_file = self.artifacts.create_text_file("CONFIGS_DUMP.txt")
            dump_file.write(self.source_project_configs.dump())
            dump_file.close()

            self.project_configs = self.source_project_configs.filter(check_if_env_set)

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

    def run_cmd(self, name, step_name, working_directory, background, code_report, pass_tag, fail_tag, *args, **kwargs):
        try:
            try:
                cmd = make_command(name)
            except CiException:
                if working_directory is None:
                    raise
                name = os.path.abspath(os.path.join(working_directory, name))
                cmd = make_command(name)
        except CiException as ex:
            self.structure.fail_current_block(unicode(ex))
            raise StepException()

        init = [self.out, self.structure, self.artifacts, self.reporter, self.server, self.settings.output,
                step_name, background]
        if code_report:
            report_file = os.path.join(working_directory, "temp_code_report.json")
            log_writer = LogWriterCodeReport(report_file, *init)
        else:
            log_writer = LogWriter(*init)

        ret = cmd(*args, _iter=True, _cwd=working_directory, _bg_exc=False, _bg=background,
                  _out=log_writer.handle_stdout, _err=log_writer.handle_stderr, **kwargs)
        log_writer.print_cmd(ret.ran)

        if background:
            self.background_processes.append({'cmd': ret, 'log': log_writer,
                                              'pass_tag': pass_tag, 'fail_tag': fail_tag})
            self.out.log("Will continue in background")
        else:
            finalize_execution(ret, log_writer, pass_tag, fail_tag)

    def execute_configuration(self, item):
        try:
            command_path = utils.strip_path_start(item["command"][0])
            working_directory = utils.parse_path(utils.strip_path_start(item.get("directory", "").rstrip("/")),
                                                 self.project_root)
            self.run_cmd(command_path,
                         item.get("name", ''),
                         working_directory,
                         item.get("background", False),
                         item.get("code_report", False),
                         item.get("pass_tag", False),
                         item.get("fail_tag", False),
                         *(item["command"][1:]))
        except KeyError as e:
            if e.message == "command":
                self.out.log("No 'command' found. Nothing to execute")
            else:
                raise

    @make_block("Reporting background steps")
    def report_background_steps(self):
        for process in self.background_processes:
            self.structure.run_in_block(finalize_execution, process['log'].step_name, False, **process)

    @make_block("Executing build steps")
    def launch_project(self):
        self.reporter.add_block_to_report(self.structure.get_current_block())
        try:
            self.structure.execute_step_structure(self.project_configs, self.execute_configuration)
            if self.background_processes:
                self.report_background_steps()
        except StepException:
            pass
            # StepException only stops build step execution,
            # not affecting other Universum functions, e.g. artifact collecting or finalizing
