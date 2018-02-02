# -*- coding: UTF-8 -*-

import os
import random
import string

import docker

__all__ = [
    "Params",
    "is_pycharm",
    "randomize_name",
    "pull_image",
    "get_image"
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
