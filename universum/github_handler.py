import json
import sys
import requests

from .modules.automation_server.jenkins_server import JenkinsServerForTrigger
from .modules.vcs.github_vcs import GithubToken
from .modules.output import needs_output
from .modules.structure_handler import needs_structure
from .lib.utils import make_block


@needs_structure
@needs_output
class GithubHandler(JenkinsServerForTrigger, GithubToken):
    """
    Excepts payload from stdin!
    """

    @staticmethod
    def define_arguments(argument_parser):
        argument_parser.add_argument('--event', '-e', dest='event', metavar="GITHUB_EVENT",
                                     help='Currently parsed from "x-github-event" header')

    def __init__(self, *args, **kwargs):
        super(GithubHandler, self).__init__(*args, **kwargs)
        self.payload = json.loads(sys.stdin.read())

    @make_block("Analysing trigger payload")
    def execute(self):
        if self.settings.event == "check_suite" and (self.payload["action"] in ["requested", "rerequested"]):
            url = self.payload["repository"]["url"]
            data = {"name": "CI tests", "head_sha": self.payload["check_suite"]["head_sha"]}
            headers = {'Authorization': f"token {self.get_token(self.payload['installation']['id'])}",
                       'Accept': 'application/vnd.github.antiope-preview+json'}
            requests.post(url=url, data=data, headers=headers)
        elif self.settings.event == "check_run" and \
                (self.payload["action"] in ["requested", "rerequested", "created"]) and \
                (self.payload["check_run"]["app"]["id"] == self.integration_id):
            self.trigger_build("some-revision")
        else:
            self.out.log("Unknown event, skipping...")

    def finalize(self):
        pass
