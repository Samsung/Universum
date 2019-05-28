# -*- coding: UTF-8 -*-

from ...lib.gravity import Module

__all__ = [
    "BaseServerForTrigger",
    "BaseServerForHostingBuild"
]


class BaseServerForTrigger(Module):
    """
    Abstract base class for API of triggering builds on automation (CI) server
    """

    def trigger_build(self, revision):  # pylint: disable=no-self-use
        raise RuntimeError("Trigger build function is not defined for current driver.")


class BaseServerForHostingBuild(Module):
    """
    Abstract base class for API of hosting CI builds on automation server
    """

    def add_build_tag(self, tag):  # pylint: disable=no-self-use
        raise RuntimeError("Tag adding function is not defined for current driver.")

    def report_build_location(self):
        raise NotImplementedError

    def artifact_path(self, local_artifacts_dir, item):
        raise NotImplementedError
