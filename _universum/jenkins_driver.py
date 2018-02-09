# -*- coding: UTF-8 -*-

from .base_classes import BuildInfoBase
from .local_driver import LocalOutput
from .module_arguments import IncorrectParameterError

__all__ = [
    "JenkinsOutput",
    "JenkinsBuildInfo"
]


JenkinsOutput = LocalOutput


class JenkinsBuildInfo(BuildInfoBase):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Jenkins variables",
                                                     "Jenkins-specific parameters")

        parser.add_argument("--jenkins-build-url", "-jbu", dest="build_url", metavar="BUILD_URL",
                            help="Link to build on Jenkins (automatically set by Jenkins)")

    def __init__(self, settings):
        self.settings = settings
        if getattr(self.settings, "build_url") is None:
            text = "Unable to retrieve Jenkins variable 'BUILD_URL'"
            raise IncorrectParameterError(text)

        self.log_link = self.settings.build_url + "console"
        self.artifact_link = self.settings.build_url + "artifact/"

    def report_build_location(self):
        return "Here is the link to build log on Jenkins: " + self.log_link

    def artifact_path(self, local_artifacts_dir, item):
        return self.artifact_link + item
