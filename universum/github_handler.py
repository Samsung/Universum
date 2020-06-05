import json
import sys
import urllib.parse

import requests

from .modules.vcs.github_vcs import GithubToken
from .modules.output import needs_output
from .modules.structure_handler import needs_structure
from .lib.utils import make_block


@needs_structure
@needs_output
class GithubHandler(GithubToken):

    @staticmethod
    def define_arguments(argument_parser):
        argument_parser.add_argument('--event', '-e', dest='event', metavar="GITHUB_EVENT",
                                     help='Currently parsed from "x-github-event" header')
        argument_parser.add_argument('--payload', '-p', dest='payload', metavar="PAYLOAD",
                                     help='<actual help coming later> leave "-" to read from stdin')
        argument_parser.add_argument('--trigger-url', '-t', dest='trigger_url', metavar="TRIGGER_URL",
                                     help='<actual help coming later> including parameters like token')

    def __init__(self, *args, **kwargs):
        # TODO: add checks for params; add tests
        super().__init__(*args, **kwargs)

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
            self.out.log(f"Sending request to {url}")
            response = requests.post(url=url, json=data, headers=headers)
            response.raise_for_status()
            self.out.log("Successfully created check run")

        elif self.settings.event == "check_run" and \
                (payload["action"] in ["requested", "rerequested", "created"]) and \
                (str(payload["check_run"]["app"]["id"]) == str(self.settings.integration_id)):

            # TODO: add parsing exception handling, add tests
            param_dict = {
                "GIT_REFSPEC": payload["check_run"]["check_suite"]["head_branch"],
                "GIT_CHECKOUT_ID": payload["check_run"]["head_sha"],
                "GITHUB_CHECK_ID": payload["check_run"]["id"],
                "GIT_REPO": payload["repository"]["clone_url"],
                "GITHUB_APP_ID": self.settings.integration_id,
                "GITHUB_INSTALLATION_ID": payload['installation']['id'],
                "GITHUB_PRIVATE_KEY": self.settings.key_path,
                "GITHUB_TOKEN": self.get_token(payload['installation']['id'])  # remove after tests
            }
            self.out.log(f"Triggering url {urllib.parse.urljoin(self.settings.trigger_url, '?...')}")
            response = requests.get(self.settings.trigger_url, params=param_dict)
            response.raise_for_status()
            self.out.log("Successfully triggered")

        else:
            self.out.log("Unhandled event, skipping...")

    def finalize(self):
        pass
