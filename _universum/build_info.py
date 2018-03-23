# -*- coding: UTF-8 -*-

from . import jenkins_driver, teamcity_driver, local_driver, utils
from .gravity import Module, Dependency

__all__ = [
    "BuildInfo"
]


class BuildInfo(Module):
    teamcity_info_factory = Dependency(teamcity_driver.TeamCityBuildInfo)
    local_info_factory = Dependency(local_driver.LocalBuildInfo)
    jenkins_info_factory = Dependency(jenkins_driver.JenkinsBuildInfo)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Environment",
                                                     "Build environment parameters")
        parser.add_argument("--build-env", "-be", dest="env", choices=["tc", "jenkins", "local"],
                            help="Type of environment to refer to (tc - TeamCity, jenkins - Jenkins, "
                                 "local - user local terminal). TeamCity and Jenkins environment "
                                 "is detected automatically when launched on build agent")

    def __init__(self, settings):
        self.driver = utils.create_diver(teamcity_factory=self.teamcity_info_factory,
                                         jenkins_factory=self.jenkins_info_factory,
                                         local_factory=self.local_info_factory,
                                         default=settings.env)

    def report_build_location(self):
        return self.driver.report_build_location()

    def artifact_path(self, local_artifacts_dir, item):
        return self.driver.artifact_path(local_artifacts_dir, item)
