import requests
from requests import Response
from ...lib import utils
from ...lib.module_arguments import ModuleArgumentParser
from .base_server import BaseServerForHostingBuild, BaseServerForTrigger


__all__ = [
    "TeamcityServer"
]


class TeamcityServer(BaseServerForHostingBuild, BaseServerForTrigger):
    @staticmethod
    def define_arguments(argument_parser: ModuleArgumentParser) -> None:
        parser = argument_parser.get_or_create_group("TeamCity variables",
                                                     "TeamCity-specific parameters")

        parser.add_argument("--tc-server", "-ts", dest="server_url", metavar="TEAMCITY_SERVER",
                            help="TeamCity server URL", type=str)
        parser.add_argument("--tc-build-id", "-tbi", dest="build_id", metavar="BUILD_ID",
                            help="teamcity.build.id", type=str)
        parser.add_argument("--tc-configuration-id", "-tci", dest="configuration_id",
                            metavar="CONFIGURATION_ID", help="system.teamcity.buildType.id", type=str)
        parser.add_argument("--tc-auth-user-id", "-tcu", dest="user_id",
                            metavar="TC_USER", help="system.teamcity.auth.userId", type=str)
        parser.add_argument("--tc-auth-passwd", "-tcp", dest="passwd",
                            metavar="TC_PASSWD", help="system.teamcity.auth.password", type=str)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        utils.check_required_option(self.settings, "server_url", """
            the URL of the TeamCity server is not specified.

            The URL of the TeamCity server is used for constructing links to builds
            and artifacts in code review system, and to adding build tags if
            requested. Please specify the server URL by using '--tc-server' ('-ts')
            command line parameter or by setting TEAMCITY_SERVER environment
            variable.""")
        utils.check_required_option(self.settings, "build_id", """
            the id of the build on TeamCity is not specified.

            The id of the build on TeamCity is used for constructing links to builds
            and artifacts in code review system, and to adding build tags if
            requested. Please specify the id of the build by using '--tc-build-id'
            ('-tbi') command line parameter or by setting BUILD_ID environment
            variable.
            
            The recommended way to define this parameter is to set BUILD_ID
            environment variable to %teamcity.build.id% in the settings of
            the top-level project on the TeamCity. 
            """)
        utils.check_required_option(self.settings, "configuration_id", """
            the id of the configuration on TeamCity is not specified.

            The id of the configuration on TeamCity is used for constructing 
            links to artifacts in code review system. Please specify the id of 
            the configuration by using '--tc-configuration-id' ('-tci')
            command line parameter or by setting CONFIGURATION_ID environment
            variable.

            The recommended way to define this parameter is to set CONFIGURATION_ID
            environment variable to %system.teamcity.buildType.id% in the settings of
            the top-level project on the TeamCity. 
            """)
        utils.check_required_option(self.settings, "user_id", """
            the id of the TeamCity user is not specified.

            The TeamCity user id is used for adding build tags. Please specify the  
            TeamCity user id by using '--tc-auth-user-id' ('-tcu') command line 
            parameter or by setting TC_USER environment variable.

            The recommended way to define this parameter is to set TC_USER
            environment variable to %system.teamcity.auth.userId% in the settings of
            the top-level project on the TeamCity.
            
            Please note that the user must have permission to add tags to build.
            """)
        utils.check_required_option(self.settings, "passwd", """
            the password of the TeamCity user is not specified.

            The TeamCity user password is used for adding build tags.
            Please specify the TeamCity user password by using '--tc-auth-passwd'
            ('-tcp') command line parameter or by setting TC_PASSWD environment
            variable.

            The recommended way to define this parameter is to set TC_PASSWD
            environment variable to %system.teamcity.auth.password% in the settings
            of the top-level project on the TeamCity.
            """)

        server_url: str = self.settings.server_url
        build_id: str = self.settings.build_id
        conf_id: str = self.settings.configuration_id
        self.tc_build_link: str = server_url + "/viewLog.html?tab=buildLog&buildId=" + build_id
        self.tc_artifact_link: str = server_url + "/repository/download/" + conf_id + "/" + build_id + ":id/"

    def report_build_location(self) -> str:
        return "Here is the link to TeamCity build: " + self.tc_build_link

    def artifact_path(self, local_artifacts_dir: str, item: str) -> str:
        return self.tc_artifact_link + item

    def add_build_tag(self, tag: str) -> Response:
        return requests.post("%s/httpAuth/app/rest/builds/id:%s/tags" %
                             (self.settings.server_url, self.settings.build_id),
                             auth=(self.settings.user_id, self.settings.passwd),
                             data=tag, headers={'Content-Type': 'text/plain'}, verify=False)
