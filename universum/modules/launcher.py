import os
import re
import sys
from inspect import cleandoc
from typing import Callable, Dict, List, Optional, TextIO, Tuple, Union
from requests import Response
import sh

from .error_state import HasErrorState
from .. import configuration_support
from ..lib import utils
from ..lib.ci_exception import CiException, CriticalCiException, StepException
from ..lib.gravity import Dependency
from ..lib.utils import make_block
from . import automation_server, api_support, artifact_collector, reporter, code_report_collector
from .output import HasOutput, Output
from .project_directory import ProjectDirectory
from .structure_handler import HasStructure

__all__ = [
    "Launcher",
    "check_if_env_set"
]


def make_command(name: str) -> sh.Command:
    try:
        return sh.Command(name)
    except sh.CommandNotFound as e:
        raise CiException(f"No such file or command as '{name}'") from e


def check_if_env_set(configuration: configuration_support.Step) -> bool:  # TODO move to configuration
    """
    Predicate function for :func:`universum.configuration_support.Configuration.filter`,
    used to decide whether this particular configuration should be executed in this
    particular environment. For more information see :ref:`filtering`

    >>> from universum.configuration_support import Configuration
    >>> c = Configuration([dict(if_env_set="MY_VAR != some value")])
    >>> check_if_env_set(c[0])
    True

    >>> c = Configuration([dict(if_env_set="MY_VAR != some value && OTHER_VAR")])
    >>> check_if_env_set(c[0])
    False

    >>> c = Configuration([dict(if_env_set="MY_VAR == some value")])
    >>> os.environ["MY_VAR"] = "some value"
    >>> check_if_env_set(c[0])
    True

    :param configuration: :class:`~universum.configuration_support.Step` object
    :return: True if environment satisfies described requirements; False otherwise
    """

    if configuration.if_env_set:
        variables = configuration.if_env_set.split("&&")
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


def check_str_match(string: str, include_substrings: List[str], exclude_substrings: List[str]) -> bool:
    """The function to check whether specified string contains 'include' and
    does NOT contain 'exclude' substrings.

    >>> check_str_match("step 1", [], [])
    True

    >>> check_str_match("step 1", ["step 1"], [])
    True

    >>> check_str_match("step 1", ["step 1"], ["step 1"])
    False

    >>> check_str_match("step 1", [], ["step 1"])
    False

    >>> check_str_match("step 1", ["step "], ["1"])
    False

    :rtype: bool
    """
    result = not include_substrings
    for substr in include_substrings:
        if substr in string:
            result = True
            break

    for substr in exclude_substrings:
        if substr in string:
            result = False
            break
    return result


def get_match_patterns(filters: Union[str, List[str]]) -> Tuple[List[str], List[str]]:
    """The function to parse 'filters' defined as a single string into the lists
    of 'include' and 'exclude' patterns.

    >>> get_match_patterns("")
    ([], [])

    >>> get_match_patterns(":")
    ([], [])

    >>> get_match_patterns(":!")
    ([], [])

    >>> get_match_patterns("f:")
    (['f'], [])

    >>> get_match_patterns("f:!f 1")
    (['f'], ['f 1'])

    >>> get_match_patterns("f:!f 1:f 2:!f 3")
    (['f', 'f 2'], ['f 1', 'f 3'])

    >>> get_match_patterns(["f", "!f 1"])
    (['f'], ['f 1'])
    """
    if not isinstance(filters, str):
        filters = ":".join(filters) if filters else ""

    include: List[str] = []
    exclude: List[str] = []

    filters = filters.split(':')
    for f in filters:
        if f.startswith('!'):
            if len(f) > 1:
                exclude.append(f[1:])
        elif f:
            include.append(f)
    return include, exclude


class RunningStep:
    # TODO: change to non-singleton module and get all dependencies by ourselves
    def __init__(self, item: configuration_support.Step,
                 out: Output,
                 fail_block: Callable[[str], None],
                 send_tag: Callable[[str], Response],
                 log_file: Optional[TextIO],
                 working_directory: str,
                 additional_environment: Dict[str, str],
                 background: bool) -> None:
        super().__init__()
        self.configuration: configuration_support.Step = item
        self.out: Output = out
        self.fail_block: Callable[[str], None] = fail_block
        self.send_tag = send_tag
        self.file: Optional[TextIO] = log_file
        self.working_directory: str = working_directory

        self.environment: Dict[str, str] = os.environ.copy()
        self.environment.update(item.environment)
        self.environment.update(additional_environment)

        self.cmd: sh.Command
        self.process: sh.RunningCommand
        self._is_background = background
        self._postponed_out: List[Tuple[Callable[[str], None], str]] = []
        self._needs_finalization: bool = True

    def prepare_command(self) -> bool:  # FIXME: refactor
        if not self.configuration.command:
            self.out.log("No 'command' found. Nothing to execute")
            return False
        command_name: str = utils.strip_path_start(self.configuration.command[0])
        try:
            try:
                self.cmd = make_command(command_name)
            except CiException:
                command_name = os.path.abspath(os.path.join(self.working_directory, command_name))
                self.cmd = make_command(command_name)
        except CiException as ex:
            self.fail_block(str(ex))
            raise StepException() from ex
        return True

    def start(self) -> None:
        if not self.prepare_command():
            self._needs_finalization = False
            return

        self._postponed_out = []
        self.process = self.cmd(*self.configuration.command[1:],
                                _iter=True,
                                _bg_exc=False,
                                _cwd=self.working_directory,
                                _env=self.environment,
                                _bg=self._is_background,
                                _out=self.handle_stdout,
                                _err=self.handle_stderr)

        log_cmd = utils.trim_and_convert_to_unicode(self.process.ran)
        self.out.log_external_command(log_cmd)
        if self.file:
            self.file.write("$ " + log_cmd + "\n")

    def handle_stdout(self, line: str = "") -> None:
        line = utils.trim_and_convert_to_unicode(line)

        if self.file:
            self.file.write(line + "\n")
        elif self._is_background:
            self._postponed_out.append((self.out.log_shell_output, line))
        else:
            self.out.log_shell_output(line)

    def handle_stderr(self, line: str) -> None:
        line = utils.trim_and_convert_to_unicode(line)
        if self.file:
            self.file.write("stderr: " + line + "\n")
        elif self._is_background:
            self._postponed_out.append((self.out.log_stderr, line))
        else:
            self.out.log_stderr(line)

    def add_tag(self, tag: str) -> None:
        if not tag:
            return

        request: Response = self.send_tag(tag)
        if request.status_code != 200:
            self.out.log_stderr(request.text)
        else:
            self.out.log("Tag '" + tag + "' added to build.")

    def finalize(self) -> None:
        if not self._needs_finalization:
            if self._is_background:
                self._is_background = False
                self.out.log("Nothing was executed: this background step had no command")
            return
        try:
            text = ""
            try:
                self.process.wait()
            except Exception as e:
                if isinstance(e, sh.ErrorReturnCode):
                    text = f"Module sh got exit code {e.exit_code}\n"
                    if e.stderr:
                        text += utils.trim_and_convert_to_unicode(e.stderr) + "\n"
                else:
                    text = str(e) + '\n'

            self._handle_postponed_out()
            if text:
                text = utils.trim_and_convert_to_unicode(text)
                if self.file:
                    self.file.write(text + "\n")
                self.fail_block(text)
                self.add_tag(self.configuration.fail_tag)
                raise StepException()

            self.add_tag(self.configuration.pass_tag)
        finally:
            self.handle_stdout()
            if self.file:
                self.file.close()
            self._is_background = False

    def _handle_postponed_out(self) -> None:
        for item in self._postponed_out:
            item[0](item[1])
        self._postponed_out = []


class Launcher(ProjectDirectory, HasOutput, HasStructure, HasErrorState):
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)
    api_support_factory = Dependency(api_support.ApiSupport)
    reporter_factory = Dependency(reporter.Reporter)
    server_factory = Dependency(automation_server.AutomationServerForHostingBuild)
    code_report_collector_factory = Dependency(code_report_collector.CodeReportCollector)

    @staticmethod
    def define_arguments(argument_parser):
        output_parser = argument_parser.get_or_create_group("Output")
        output_parser.add_argument("--out", "-o", dest="output", choices=["console", "file"],
                                   help="Define whether to print build logs to console or file. "
                                        "Log file names are generated based on the names of build steps. "
                                        "By default, logs are printed to console when the build is launched on "
                                        "Jenkins or TeamCity agent")

        parser = argument_parser.get_or_create_group("Configuration execution",
                                                     "External command launching and reporting parameters")

        parser.add_argument("--config", "-cfg", dest="config_path", metavar="CONFIG_PATH",
                            help="Path to project configuration file (example: -cfg=my/prject/my_conf.py). "
                                 "Default is ``.universum.py``")

        parser.add_argument("--filter", "-f", dest="step_filter", action='append', metavar="STEP_FILTER",
                            help="Filter steps to execute. A single filter or a set of filters separated by ':'. "
                                 "Exclude using '!' symbol before filter. "
                                 "Example: -f='str1:!not str2' OR -f='str1' -f='!not str2'. "
                                 "See online documentation for more details")

        parser.add_hidden_argument("--launcher-output", "-lo", dest="output", choices=["console", "file"],
                                   help="Deprecated option. Please use '--out' instead", is_hidden=True)
        parser.add_hidden_argument("--launcher-config-path", "-lcp", dest="config_path", is_hidden=True,
                                   help="Deprecated option. Please use '--steps-config' instead")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.source_project_configs: configuration_support.Configuration
        self.project_config: configuration_support.Configuration = configuration_support.Configuration()

        self.output: Output = self.settings.output
        if self.output is None:
            if utils.detect_environment() == "terminal":
                self.output = "file"
            else:
                self.output = "console"

        self.config_path = self.settings.config_path
        if not self.config_path:
            self.config_path = ".universum.py"

        self.artifacts = self.artifacts_factory()
        self.api_support = self.api_support_factory()
        self.reporter = self.reporter_factory()
        self.server = self.server_factory()
        self.code_report_collector = self.code_report_collector_factory()
        self.include_patterns, self.exclude_patterns = get_match_patterns(self.settings.step_filter)

    @make_block("Processing project configs")
    def process_project_configs(self) -> configuration_support.Configuration:
        config_path = utils.parse_path(self.config_path, self.settings.project_root)
        configuration_support.set_project_root(self.settings.project_root)
        config_globals: Dict[str, configuration_support.Configuration] = {}
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        sys.path.append(os.path.join(os.path.dirname(config_path)))

        try:
            with open(config_path, encoding="utf-8") as config_file:
                exec(config_file.read(), config_globals)  # pylint: disable=exec-used
            self.source_project_configs = config_globals["configs"]
            dump_file: TextIO = self.artifacts.create_text_file("CONFIGS_DUMP.txt")
            dump_file.write(self.source_project_configs.dump())
            dump_file.close()
            config = self.source_project_configs.filter(check_if_env_set)
            self.project_config = config.filter(
                lambda cfg: check_str_match(cfg.name, self.include_patterns, self.exclude_patterns))

        except IOError as e:
            text = f"""{e}\n
                Possible reasons of this error:\n
                * There is no Universum configuration file in project repository\n
                * Config path, passed to the script ('{self.config_path}'),
                  does not lead to actual Universum configuration file location\n
                * Some problems occurred while downloading or copying the repository
                """
            raise CriticalCiException(cleandoc(text)) from e
        except KeyError as e:
            text = "KeyError: " + str(e) + '\n'
            text += "Possible reason of this error: variable 'configs' is not defined in Universum configuration file"
            raise CriticalCiException(text) from e
        except Exception as e:
            ex_traceback = sys.exc_info()[2]
            text = "Exception while processing Universum configuration file:\n" + \
                   utils.format_traceback(e, ex_traceback) + \
                   "\nTry to execute ``confgs.dump()`` to make sure no exceptions occur in that case."
            raise CriticalCiException(text) from e
        return self.project_config

    def create_process(self, item: configuration_support.Step) -> RunningStep:
        working_directory = utils.parse_path(utils.strip_path_start(item.directory.rstrip("/")),
                                             self.settings.project_root)

        # get_current_block() should be called while inside the required block, not afterwards
        block = self.structure.get_current_block()

        def fail_block(line: str = "") -> None:
            self.structure.fail_block(block, line)

        log_file: Optional[TextIO] = None
        if self.output == "file":
            log_file = self.artifacts.create_text_file(item.name + "_log.txt")
            self.out.log("Execution log is redirected to file")

        additional_environment = self.api_support.get_environment_settings()
        return RunningStep(item, self.out, fail_block, self.server.add_build_tag,
                    log_file, working_directory, additional_environment, item.background)

    def launch_custom_configs(self, custom_configs: configuration_support.Configuration) -> None:
        self.structure.execute_step_structure(custom_configs, self.create_process)

    @make_block("Executing build steps")
    def launch_project(self) -> None:
        self.reporter.add_block_to_report(self.structure.get_current_block())
        self.structure.execute_step_structure(self.project_config, self.create_process)
