import requests

from .modules.automation_server.jenkins_server import JenkinsServerForTrigger
from .modules.vcs.github_vcs import GithubToken
from .modules.output import needs_output
from .modules.structure_handler import needs_structure
from .lib.utils import make_block


@needs_structure
@needs_output
class GithubHandler(JenkinsServerForTrigger, GithubToken):

    @staticmethod
    def define_arguments(argument_parser):
        argument_parser.add_argument('--event', '-e', dest='header', metavar="GITHUB_EVENT",
                                     help='Currently parsed from "x-github-event" header')
        argument_parser.add_argument('--payload', '-op', dest='payload', metavar="GITHUB_PAYLOAD",
                                     help='Payload JSON object')

    def __init__(self, *args, **kwargs):
        super(GithubHandler, self).__init__(*args, **kwargs)

    @make_block("Analysing trigger payload")
    def execute(self):
        if self.settings.header == "check_suite" and (self.settings.payload["action"] in ["requested", "rerequested"]):
            url = self.settings.payload["repository"]["url"]
            data = {"name": "CI tests", "head_sha": self.settings.payload["check_suite"]["head_sha"]}
            headers = {'Authorization': f"token {self.token}", 'Accept': 'application/vnd.github.antiope-preview+json'}
            requests.post(url=url, data=data, headers=headers)
        elif self.settings.header == "check_run" and \
                (self.settings.payload["action"] in ["requested", "rerequested", "created"]) and \
                (self.settings.payload["check_run"]["app"]["id"] == self.settings.integration_id):
            self.trigger_build("some-revision")
        else:
            self.out.log("Unknown event, skipping...")

    def finalize(self):
        pass
