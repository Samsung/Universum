# -*- coding: UTF-8 -*-

from ...lib.gravity import Dependency, Module
from ...lib import utils
from .jenkins_server import JenkinsServerForHostingBuild, JenkinsServerForTrigger
from .local_server import LocalServer
from .teamcity_server import TeamcityServer

__all__ = [
    "AutomationServerForHostingBuild",
    "AutomationServerForTrigger"
]


class AutomationServer(Module):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Automation server", "Automation server options")
        parser.add_argument("--server-type", "-st", dest="type", choices=["tc", "jenkins", "local"],
                            help="Type of environment to refer to (tc - TeamCity, jenkins - Jenkins, "
                                 "local - user local terminal). TeamCity and Jenkins environment "
                                 "is detected automatically when launched on build agent")


class AutomationServerForHostingBuild(AutomationServer):
    teamcity_driver_factory = Dependency(TeamcityServer)
    local_driver_factory = Dependency(LocalServer)
    jenkins_driver_factory = Dependency(JenkinsServerForHostingBuild)

    def __init__(self, *args, **kwargs):
        super(AutomationServerForHostingBuild, self).__init__(*args, **kwargs)
        self.driver = utils.create_driver(teamcity_factory=self.teamcity_driver_factory,
                                          jenkins_factory=self.jenkins_driver_factory,
                                          local_factory=self.local_driver_factory,
                                          default=self.settings.type)

    def report_build_location(self):
        return self.driver.report_build_location()

    def artifact_path(self, local_artifacts_dir, item):
        return self.driver.artifact_path(local_artifacts_dir, item)

    def add_build_tag(self, tag):
        return self.driver.add_build_tag(tag)


class AutomationServerForTrigger(AutomationServer):
    teamcity_driver_factory = Dependency(TeamcityServer)
    local_driver_factory = Dependency(LocalServer)
    jenkins_driver_factory = Dependency(JenkinsServerForTrigger)

    def __init__(self, *args, **kwargs):
        super(AutomationServerForTrigger, self).__init__(*args, **kwargs)
        self.driver = utils.create_driver(teamcity_factory=self.teamcity_driver_factory,
                                          jenkins_factory=self.jenkins_driver_factory,
                                          local_factory=self.local_driver_factory,
                                          default=self.settings.type)

    def trigger_build(self, revision):
        return self.driver.trigger_build(revision)

