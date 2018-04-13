# -*- coding: UTF-8 -*-

from ..base_classes import AutomationServerDriverBase

__all__ = [
    "LocalServer"
]


class LocalServer(AutomationServerDriverBase):

    def report_build_location(self):
        return "Local build. No external logs provided"

    def artifact_path(self, local_artifacts_dir, item):
        return local_artifacts_dir + "/" + item
