# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import datetime
import os
import random
import socket
import string
import six
from six.moves import range

from universum import submit, poll, main
from universum.lib import gravity
from tests.thirdparty.pyfeed.rfc3339 import tf_from_timestamp
from . import default_args

__all__ = [
    "Params",
    "is_pycharm",
    "randomize_name",
    "get_open_port",
    "python_time_from_rfc3339_time",
    "is_container_outdated",
    "create_empty_settings",
    "TestEnvironment"
]


class Params:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def is_pycharm():
    return "PYCHARM_HOSTED" in os.environ


def randomize_name(name):
    return name + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def get_open_port():
    temp = socket.socket()
    temp.bind(("", 0))
    result = temp.getsockname()[1]
    temp.close()
    return result


def python_time_from_rfc3339_time(rfc3339_time):
    return tf_from_timestamp(rfc3339_time)


def is_container_outdated(container):
    created = python_time_from_rfc3339_time(container.attrs["Created"])
    delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(created)
    if abs(delta).days > 7:
        return True
    return False


def create_empty_settings(test_type):
    if test_type == "poll":
        main_class = poll.Poll
    elif test_type == "submit":
        main_class = submit.Submit
    elif test_type == "main":
        main_class = main.Main
    else:
        assert False, "create_empty_settings expects test_type parameter to be poll, submit or main"
    argument_parser = default_args.ArgParserWithDefault()
    argument_parser.set_defaults(main_class=main_class)
    gravity.define_arguments_recursive(main_class, argument_parser)
    settings = argument_parser.parse_args([])
    return settings


simple_test_config = """
from universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""


class TestEnvironment:
    def __init__(self, temp_dir, test_type):
        self.temp_dir = temp_dir
        self.settings = create_empty_settings(test_type)
        if test_type == "poll":
            self.settings.Poll.db_file = self.db_file
            self.settings.JenkinsServerForTrigger.trigger_url = "https://localhost/?cl=%s"
            self.settings.AutomationServer.type = "jenkins"
            self.settings.ProjectDirectory.project_root = six.text_type(self.temp_dir.mkdir("project_root"))
        elif test_type == "submit":
            self.settings.Submit.commit_message = "Test CL"
            # For submitter, the main working dir (project_root) should be the root
            # of the VCS workspace/client
            self.settings.ProjectDirectory.project_root = six.text_type(self.vcs_cooking_dir)
        elif test_type == "main":
            configs_file = self.temp_dir.join("configs.py")
            configs_file.write(simple_test_config)
            self.settings.Launcher.config_path = six.text_type(configs_file)
            self.settings.ArtifactCollector.artifact_dir = six.text_type(self.temp_dir.mkdir("artifacts"))
            # The project_root directory must not exist before launching main
            self.settings.ProjectDirectory.project_root = six.text_type(self.temp_dir.join("project_root"))

        self.settings.Output.type = "term"

    def get_last_change(self):
        raise NotImplementedError()

    def file_present(self, file_path):
        raise NotImplementedError()

    def text_in_file(self, text, file_path):
        raise NotImplementedError()

    def make_a_change(self):
        raise NotImplementedError()
