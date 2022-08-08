from ..error_state import HasErrorState
from ...lib.module_arguments import ModuleArgumentParser
from .base_server import BaseServerForHostingBuild, BaseServerForTrigger

__all__ = [
    "GithubServer",
]


class GithubServer(BaseServerForHostingBuild, BaseServerForTrigger, HasErrorState):
    @staticmethod
    def define_arguments(argument_parser: ModuleArgumentParser) -> None:
        parser = argument_parser.get_or_create_group("Github Actions variables",
                                                     "Github Actions specific parameters")

        parser.add_argument("--github-server", "-ghs", dest="server_url", metavar="GITHUB_SERVER_URL",
                            help="Github server URL", type=str)
        parser.add_argument("--github-repo", "-ghr", dest="repo", metavar="GITHUB_REPOSITORY",
                            help="Github owner and repository name. For example, octocat/Hello-World", type=str)
        parser.add_argument("--github-run-id", "-ghri", dest="run_id", metavar="GITHUB_RUN_ID",
                            help="Github run ID", type=str)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.check_required_option("server_url", """
            The URL of the Github server is not specified.
            
            The URL of the Github server is used for constructing links to builds in code review system.

            Please specify the github server url by using '--github-server' ('-ghs') command-line
            option or GITHUB_SERVER_URL environment variable.
            """)
        self.check_required_option("repo", """
            The Github repository is not specified.
            
            The name of the Github repository is used for constructing links to builds in code review system.

            Please specify the Github repository by using '--github-repo' ('-ghr') command-line
            option or GITHUB_REPOSITORY environment variable.
            """)
        self.check_required_option("run_id", """
            The Github run ID is not specified.
            
            The id of the run on Github is used for constructing links to builds in code review system.

            Please specify the Github repository by using '--github-run-id' ('-ghri') command-line
            option or GITHUB_RUN_ID environment variable.
            """)

    def report_build_location(self) -> str:
        build_link: str = f"{self.settings.server_url}/{self.settings.repo}/actions/runs/{self.settings.run_id}"
        return "Here is the link to Github Actions build: " + build_link

    def artifact_path(self, local_artifacts_dir: str, item: str) -> str:
        return "/Artifact/not/exist"
