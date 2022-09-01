from ..error_state import HasErrorState
from ...lib.module_arguments import ModuleArgumentParser
from .base_server import BaseServerForHostingBuild, BaseServerForTrigger

__all__ = [
    "GithubServer",
]


class GithubServer(BaseServerForHostingBuild, BaseServerForTrigger, HasErrorState):
    @staticmethod
    def define_arguments(argument_parser: ModuleArgumentParser) -> None:
        parser = argument_parser.get_or_create_group(
            "GitHub Actions variables",
            "GitHub sets these environment variables and usually do not need to set these arguments. See: https://"
            "docs.github.com/en/actions/learn-github-actions/environment-variables#default-environment-variables"
        )
        parser.add_argument("--github-server", dest="server_url", metavar="GITHUB_SERVER_URL",
                            help="GitHub server URL, used on GitHub Actions for constructing links to builds. "
                                 "For example: https://github.com", type=str)
        parser.add_argument("--github-repo", dest="repo", metavar="GITHUB_REPOSITORY",
                            help="GitHub owner and repository name, used on GitHub Actions for constructing links to "
                                 "builds. For example: octocat/Hello-World", type=str)
        parser.add_argument("--github-run-id", dest="run_id", metavar="GITHUB_RUN_ID",
                            help="GitHub run ID, used on GitHub Actions for constructing links to builds."
                                 "For example: 1658821493", type=str)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.check_required_option("server_url", """
            The URL of the GitHub server is not specified.
            
            The URL of the GitHub server is used for constructing links to builds in code review system.

            Please specify the GitHub server url by using '--github-server'command-line  option or GITHUB_SERVER_URL 
            environment variable.
            """)
        self.check_required_option("repo", """
            The GitHub repository is not specified.
            
            The name of the GitHub repository is used for constructing links to builds in code review system.

            Please specify the GitHub repository by using '--github-repo' command-line option or 
            GITHUB_REPOSITORY environment variable.
            """)
        self.check_required_option("run_id", """
            The GitHub run ID is not specified.
            
            The id of the run on GitHub is used for constructing links to builds in code review system.

            Please specify the Github repository by using '--github-run-id' command-line option or 
            GITHUB_RUN_ID environment variable.
            """)

    def report_build_location(self) -> str:
        build_link: str = f"{self.settings.server_url}/{self.settings.repo}/actions/runs/{self.settings.run_id}"
        return "Here is the link to Github Actions build: " + build_link

    def artifact_path(self, local_artifacts_dir: str, item: str) -> str:
        return item
