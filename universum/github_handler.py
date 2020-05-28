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
            url = self.payload["repository"]["url"] + "/check-runs"
            data = {"name": "CI tests", "head_sha": self.payload["check_suite"]["head_sha"]}
            headers = {'Authorization': f"token {self.get_token(self.payload['installation']['id'])}",
                       'Accept': 'application/vnd.github.antiope-preview+json'}
            response = requests.post(url=url, json=data, headers=headers)
            self.out.log(f"Got response {response.status_code} with message '{response.text}'")
        elif self.settings.event == "check_run" and \
                (self.payload["action"] in ["requested", "rerequested", "created"]) and \
                (self.payload["check_run"]["app"]["id"] == self.settings.integration_id):
            self.trigger_build({
                "GIT_REFSPEC": self.payload["check_run"]["check_suite"]["head_branch"],
                "GIT_CHECKOUT_ID": self.payload["check_run"]["head_sha"],
                "GITHUB_CHECK_ID": self.payload["check_run"]["id"],
                "GIT_REPO": self.payload["repository"]["clone_url"],
                "GITHUB_INTEGRATION": self.settings.integration_id,
                "GITHUB_INSTALLATION": self.payload['installation']['id'],
                "GITHUB_PRIVATE_KEY": self.settings.key_path
            })
        else:
            self.out.log("Unknown event, skipping...")

    def finalize(self):
        pass
