# -*- coding: UTF-8 -*-

import requests

from ...lib.module_arguments import IncorrectParameterError
from .base_server import BaseServer

__all__ = [
    "TeamcityServer"
]


class TeamcityServer(BaseServer):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("TeamCity variables",
                                                     "TeamCity-specific parameters")

        parser.add_argument("--tc-server", "-ts", dest="server_url", metavar="TEAMCITY_SERVER",
                            help="TeamCity server URL")
        parser.add_argument("--tc-build-id", "-tbi", dest="build_id", metavar="BUILD_ID",
                            help="teamcity.build.id")
        parser.add_argument("--tc-configuration-id", "-tci", dest="configuration_id",
                            metavar="CONFIGURATION_ID", help="system.teamcity.buildType.id")
        parser.add_argument("--tc-auth-user-id", "-tcu", dest="user_id",
                            metavar="TC_USER", help="system.teamcity.auth.userId")
        parser.add_argument("--tc-auth-passwd", "-tcp", dest="passwd",
                            metavar="TC_PASSWD", help="system.teamcity.auth.password")

    def check_required_option(self, name, option, env_var):
        if not getattr(self.settings, name, None):
            raise IncorrectParameterError("the mandatory TeamCity setting '" + name + "' is not set\n\n"
                                          "Please use command-line option '" + option + "'\n"
                                          "or set the environment variable '" + env_var + "'")

    def __init__(self, *args, **kwargs):
        super(TeamcityServer, self).__init__(*args, **kwargs)
        self.check_required_option("server_url", "--tc-server", "TEAMCITY_SERVER")
        self.check_required_option("build_id", "--tc-build-id", "BUILD_ID")
        self.check_required_option("configuration_id", "--tc-configuration-id", "CONFIGURATION_ID")
        self.check_required_option("user_id", "--tc-auth-user-id", "TC_USER")
        self.check_required_option("passwd", "--tc-auth-passwd", "TC_PASSWD")

        self.tc_build_link = self.settings.server_url + "/viewLog.html?tab=buildLog&buildId=" + self.settings.build_id
        self.tc_artifact_link = self.settings.server_url + "/repository/download/" + \
            self.settings.configuration_id + "/" + self.settings.build_id + ":id/"

    def report_build_location(self):
        return "Here is the link to TeamCity build: " + self.tc_build_link

    def artifact_path(self, local_artifacts_dir, item):
        return self.tc_artifact_link + item

    def add_build_tag(self, tag):
        return requests.post("%s/httpAuth/app/rest/builds/id:%s/tags" %
                             (self.settings.server_url, self.settings.build_id),
                             auth=(self.settings.user_id, self.settings.passwd),
                             data=tag, headers={'Content-Type': 'text/plain'}, verify=False)
