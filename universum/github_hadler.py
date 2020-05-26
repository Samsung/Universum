from .modules.automation_server.jenkins_server import JenkinsServerForTrigger

from .lib.utils import make_block


class GithubHandler(JenkinsServerForTrigger):

    @staticmethod
    def define_arguments(argument_parser):
        argument_parser.add_argument('--event', '-e', dest='header', metavar="GITHUB_EVENT",
                                     help='Currently parsed from "x-github-event" header')
        argument_parser.add_argument('--payload', '-op', dest='json', metavar="GITHUB_PAYLOAD",
                                     help='Payload JSON object')

    def __init__(self, *args, **kwargs):
        super(GithubHandler, self).__init__(*args, **kwargs)

    @make_block("Enumerating changes")
    def execute(self):
        pass

    def finalize(self):
        pass
