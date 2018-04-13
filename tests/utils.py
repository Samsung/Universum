# -*- coding: UTF-8 -*-

import os
import random
import string

import docker

from _universum import gravity
import poll
import submit
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

        image = client.images.pull(registry + "/" + image_name)
        image.tag(image_name, "latest")
    except docker.errors.APIError as e:
        print unicode(e)

    return image


def get_image(request, client, params, name):
    try:
        image = client.images.get(name)
    except docker.errors.ImageNotFound:
        print "'%s' image is not found locally,  trying to pull from registry" % name
        image = pull_image(client, params, name)

    if image is None:
        request.raiseerror("Cannot find docker image '%s'. Try building it manually\n" % name)

    return image


def create_settings(class_name):
    argument_parser = default_args.ArgParserWithDefault()
    gravity.define_arguments_recursive(class_name, argument_parser)
    return argument_parser.parse_args([])


class TestEnvironment(object):
    def __init__(self, test_type):
        if test_type == "poll":
            self.settings = create_settings(poll.Poller)
            self.settings.Poller.db_file = self.db_file
            self.settings.JenkinsServer.trigger_url = "https://localhost/?cl=%s"
            self.settings.AutomationServer.type = "jenkins"
        else:
            self.settings = create_settings(submit.Submit)
            self.settings.Submit.commit_message = "Test CL"
            self.settings.FileManager.project_root = unicode(self.root_directory)
        self.settings.Output.type = "term"

    def get_last_change(self):
        raise NotImplementedError()

    def file_present(self, file_path):
        raise NotImplementedError()

    def text_in_file(self, text, file_path):
        raise NotImplementedError()

    def make_a_change(self):
        raise NotImplementedError()
