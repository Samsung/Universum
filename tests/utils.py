# -*- coding: UTF-8 -*-

import os
import random
import socket
import string

import docker

from _universum import submit, poll, main
from _universum.lib import gravity
from . import default_args

__all__ = [
    "Params",
    "is_pycharm",
    "randomize_name",
    "pull_image",
    "get_image",
    "create_settings",
    "TestEnvironment"
]


class Params(object):
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


def pull_image(client, params, image_name):
    image = None

    if params is None:
        print "Docker registry parameters are not set, pull is skipped"
        return image

    try:
        registry = params.url
        client.login(params.login, registry=registry, password=params.password, reauth=True)
        if registry.startswith("https://"):
            registry = registry[8:]
        if registry.startswith("http://"):
            registry = registry[7:]

        image = client.images.pull(registry + "/" + image_name, tag="latest")
        image.tag(image_name)
    except docker.errors.APIError as e:
        print unicode(e)

    return image


def get_image(request, client, params, name):
    try:
        image = client.images.get(name)
    except docker.errors.ImageNotFound:
        print "'%s' image not found locally, trying to pull from registry" % name
        image = pull_image(client, params, name)

    if image is None:
        try:
            print "'%s' image not found in registry, trying to pull by name" % name
            image = client.images.pull(name)
        except docker.errors.ImageNotFound:
            request.raiseerror("Cannot find docker image '%s'. Try building it manually\n" % name)

    return image


def create_settings(class_name):
    argument_parser = default_args.ArgParserWithDefault()
    argument_parser.set_defaults(main_class=class_name)
    gravity.define_arguments_recursive(class_name, argument_parser)
    return argument_parser.parse_args([])


simple_test_config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""


class TestEnvironment(object):
    def __init__(self, directory, test_type):
        if test_type == "poll":

            self.settings = create_settings(poll.Poll)
            self.settings.subcommand = "poll"

            self.settings.Poll.db_file = self.db_file
            self.settings.JenkinsServer.trigger_url = "https://localhost/?cl=%s"
            self.settings.AutomationServer.type = "jenkins"
            self.settings.ProjectDirectory.project_root = unicode(directory.mkdir("project_root"))
        elif test_type == "submit":

            self.settings = create_settings(submit.Submit)
            self.settings.subcommand = "submit"

            self.settings.Submit.commit_message = "Test CL"
            # For submitter, the main working dir (project_root) should be the root
            # of the VCS workspace/client
            self.settings.ProjectDirectory.project_root = unicode(self.vcs_cooking_dir)
        elif test_type == "main":

            self.settings = create_settings(main.Main)

            configs_file = directory.join("configs.py")
            configs_file.write(simple_test_config)
            self.settings.Launcher.config_path = unicode(configs_file)
            self.settings.ArtifactCollector.artifact_dir = unicode(directory.mkdir("artifacts"))
            # The project_root directory must not exist before launching main
            self.settings.ProjectDirectory.project_root = unicode(directory.join("project_root"))
        else:
            assert False, "TestEnvironment expects test_type parameter to be poll, submit or main"
        self.settings.Output.type = "term"

    def get_last_change(self):
        raise NotImplementedError()

    def file_present(self, file_path):
        raise NotImplementedError()

    def text_in_file(self, text, file_path):
        raise NotImplementedError()

    def make_a_change(self):
        raise NotImplementedError()
