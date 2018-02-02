# -*- coding: UTF-8 -*-

from .base_classes import OutputBase, BuildInfoBase
from .module_arguments import IncorrectParameterError

__all__ = [
    "TeamCityOutput",
    "TeamCityBuildInfo"
]


def escape(message):
    return message.replace('\r', '').replace('|', '||').replace('\'', '|\'').replace('[', '|[').replace(']', '|]')


class TeamCityOutput(OutputBase):
    def open_block(self, num_str, name):
        print "##teamcity[blockOpened name='{} {}']".format(num_str, escape(name))

    def close_block(self, num_str, name, status):
        print "##teamcity[blockClosed name='{} {}']".format(num_str, escape(name))

    def report_error(self, description):
        print "##teamcity[buildProblem description='<{}>']".format(escape(description))

    def change_status(self, message):
        print "##teamcity[buildStatus text='{}']".format(escape(message))

    def log_exception(self, line):
        lines = line.split("\n")
        for single_line in lines:
            print u"##teamcity[message text='{}' status='ERROR']".format(escape(single_line))

    def log_stderr(self, line):
        lines = line.split("\n")
        for single_line in lines:
            print u"##teamcity[message text='{}' status='WARNING']".format(escape(single_line))

    def log(self, line):
        print "==>", line

    def log_external_command(self, command):
        print "$", command

    def log_shell_output(self, line):
        print line


class TeamCityBuildInfo(BuildInfoBase):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("TeamCity variables",
                                                     "TeamCity-specific parameters")

        parser.add_argument("--tc-server", "-ts", dest="server_url", metavar="TEAMCITY_SERVER",
                            help="TeamCity server URL")
        parser.add_argument("--tc-build-id", "-tbi", dest="build_id", metavar="BUILD_ID",
                            help="teamcity.build.id")
        parser.add_argument("--tc-configuration-id", "-tci", dest="configuration_id",
                            metavar="CONFIGURATION_ID", help="system.teamcity.byildType.id")

    def check_required_option(self, name, env_var):
        if getattr(self.settings, name) is None:
            text = "Unable to retrieve TeamCity variable '" + env_var + "'"
            raise IncorrectParameterError(text)

    def __init__(self, settings):
        self.settings = settings
        self.check_required_option("server_url", "TEAMCITY_SERVER")
        self.check_required_option("build_id", "BUILD_ID")
        self.check_required_option("configuration_id", "CONFIGURATION_ID")

        self.tc_build_link = self.settings.server_url + "/viewLog.html?tab=buildLog&buildId=" + self.settings.build_id
        self.tc_artifact_link = self.settings.server_url + "/repository/download/" + \
            self.settings.configuration_id + "/" + self.settings.build_id + ":id/"

    def report_build_location(self):
        return "Here is the link to TeamCity build: " + self.tc_build_link

    def artifact_path(self, local_artifacts_dir, item):
        return self.tc_artifact_link + item
