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

    @staticmethod
    def define_arguments(argument_parser):
        argument_parser.add_argument('--event', '-e', dest='event', metavar="GITHUB_EVENT",
                                     help='Currently parsed from "x-github-event" header')
        argument_parser.add_argument('--payload', '-p', dest='payload', metavar="PAYLOAD",
                                     help='<actual help coming later> leave "-" to read from stdin')

    def __init__(self, *args, **kwargs):
        super(GithubHandler, self).__init__(*args, **kwargs)
        # TODO: add checks for params; add tests

    @make_block("Analysing trigger payload")
    def execute(self):
        # TODO: refactor to real curl-style variable with '@' adn '-' support
        # TODO: add some proper exception handling on payload contents; add tests
        if self.settings.payload == '-':
            payload = json.loads(sys.stdin.read())
        else:
            payload = json.loads(self.settings.payload)

        if self.settings.event == "check_suite" and (payload["action"] in ["requested", "rerequested"]):
            url = payload["repository"]["url"] + "/check-runs"
            data = {"name": "CI tests", "head_sha": payload["check_suite"]["head_sha"]}
            headers = {'Authorization': f"token {self.get_token(payload['installation']['id'])}",
                       'Accept': 'application/vnd.github.antiope-preview+json'}
            response = requests.post(url=url, json=data, headers=headers)
            response.raise_for_status()

        elif self.settings.event == "check_run" and \
                (payload["action"] in ["requested", "rerequested", "created"]) and \
                (str(payload["check_run"]["app"]["id"]) == str(self.settings.integration_id)):
            self.trigger_build({
                "GIT_REFSPEC": payload["check_run"]["check_suite"]["head_branch"],
                "GIT_CHECKOUT_ID": payload["check_run"]["head_sha"],
                "GITHUB_CHECK_ID": payload["check_run"]["id"],
                "GIT_REPO": payload["repository"]["clone_url"],
                "GITHUB_APP_ID": self.settings.integration_id,
                "GITHUB_INSTALLATION_ID": payload['installation']['id'],
                "GITHUB_PRIVATE_KEY": self.settings.key_path,
                "GITHUB_TOKEN": self.get_token(payload['installation']['id'])  # remove after tests
            })

        else:
            self.out.log("Unhandled event, skipping...")

    def finalize(self):
        pass
