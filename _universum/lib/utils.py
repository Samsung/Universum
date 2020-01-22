# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import codecs
import imp
import inspect
import os
import sys
import traceback
import six

from _universum.lib.ci_exception import CiException
from .ci_exception import CriticalCiException, SilentAbortException
from .module_arguments import IncorrectParameterError

__all__ = [
    "strip_path_start",
    "parse_path",
    "calculate_file_absolute_path",
    "detect_environment",
    "create_driver",
    "format_traceback",
    "check_required_option",
    "catch_exception",
    "import_module",
    "trim_and_convert_to_unicode",
    "convert_to_str",
    "unify_argument_list",
    "Uninterruptible",
    "make_block",
    "check_request_result"
]


def strip_path_start(line):
    if line.startswith("./"):
        return line[2:]
    return line


def parse_path(path, starting_point):
    if path.startswith('/'):
        path = os.path.join(path)
    else:
        path = os.path.join(starting_point, path)

    return os.path.abspath(path)


def calculate_file_absolute_path(target_directory, file_basename):
    name = file_basename.replace(" ", "_")
    name = name.replace("/", "\\")
    if name.startswith('_'):
        name = name[1:]
    return os.path.join(target_directory, name)


def detect_environment():
    """
    :return: "tc" if the script is launched on TeamCity agent,
             "jenkins" is launched on Jenkins agent,
             "terminal" otherwise
    """
    teamcity = "TEAMCITY_VERSION" in os.environ
    jenkins = "JENKINS_HOME" in os.environ
    pycharm = "PYCHARM_HOSTED" in os.environ
    if pycharm:
        return "terminal"
    if teamcity and not jenkins:
        return "tc"
    if not teamcity and jenkins:
        return "jenkins"
    return "terminal"


def create_driver(local_factory, teamcity_factory, jenkins_factory, env_type=""):
    if not env_type:
        env_type = detect_environment()

    if env_type == "tc":
        return teamcity_factory()
    if env_type == "jenkins":
        return jenkins_factory()
    return local_factory()


def format_traceback(exc, trace):
    tb_lines = traceback.format_exception(exc.__class__, exc, trace)
    tb_text = ''.join(tb_lines)
    return tb_text


def check_required_option(settings, setting_name, error_message):
    if not getattr(settings, setting_name, None):
        raise IncorrectParameterError(inspect.cleandoc(error_message))


def catch_exception(exception_name, ignore_if=None):
    def decorated_function(function):
        def function_to_run(*args, **kwargs):
            result = None
            try:
                result = function(*args, **kwargs)
                return result
            except Exception as e:
                if not type(e).__name__ == exception_name:
                    raise
                if ignore_if is not None:
                    if ignore_if in str(e):
                        return result
                raise CriticalCiException(six.text_type(e)) #TODO: try to remove 'six.text_type' usage
        return function_to_run
    return decorated_function


def import_module(name, path=None, target_name=None):
    try:
        return sys.modules[name]
    except KeyError:
        filename = None
        if not target_name:
            target_name = name
        try:
            filename, pathname, description = imp.find_module(name, path)
            return imp.load_module(target_name, filename, pathname, description)
        finally:
            if filename:
                filename.close()


def trim_and_convert_to_unicode(line):
    if isinstance(line, str):
        pass
    elif not isinstance(line, six.text_type):
        line = six.text_type(line)

    if line.endswith("\n"):
        line = line[:-1]

    return line


def convert_to_str(line):
    if isinstance(line, bytes):
        return line.decode("utf8", "replace")
    return str(line)



def unify_argument_list(source_list, separator=',', additional_list=None):
    if additional_list is None:
        resulting_list = []
    else:
        resulting_list = additional_list

    # Add arguments parsed by ModuleArgumentParser, including list elements generated by nargs='+'
    if source_list is not None:
        for item in source_list:
            if isinstance(item, list):
                resulting_list.extend(item)
            else:
                resulting_list.append(item)

    # Remove None and empty elements added by previous steps
    resulting_list = [item for item in resulting_list if item]

    # Split one-element arguments and merge to one list
    resulting_list = [item.strip() for entry in resulting_list for item in entry.strip('"\'').split(separator)]

    return resulting_list


class Uninterruptible:
    def __init__(self, error_logger):
        self.return_code = 0
        self.error_logger = error_logger
        self.exceptions = []

    def __enter__(self):
        def excepted_function(func, *args, **kwargs):
            try:
                func(*args, **kwargs)
            except SilentAbortException as e:
                self.return_code = max(self.return_code, e.application_exit_code)
            except (KeyboardInterrupt, SystemExit):
                self.error_logger("Interrupted from outer scope\n")
                self.return_code = 3
            except Exception as e:
                ex_traceback = sys.exc_info()[2]
                self.exceptions.append(format_traceback(e, ex_traceback))
                self.return_code = max(self.return_code, 2)
        return excepted_function

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.return_code == 2:
            for entry in self.exceptions:
                sys.stderr.write(entry)
        if self.return_code != 0:
            raise SilentAbortException(application_exit_code=self.return_code)


def make_block(block_name, pass_errors=True):
    def decorated_function(func):
        def function_in_block(self, *args, **kwargs):
            return self.structure.run_in_block(func, block_name, pass_errors, self, *args, **kwargs)
        return function_in_block
    return decorated_function


def check_request_result(result):
    if result.status_code != 200:
        text = "Invalid return code " + six.text_type(result.status_code) + ". Response is:\n"
        text += result.text
        raise CiException(text)
