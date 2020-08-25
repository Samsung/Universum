import json
import urllib.parse

from .modules.vcs.github_vcs import GithubToken
from .modules.output import HasOutput
from .modules.structure_handler import HasStructure
from .lib.ci_exception import CriticalCiException
from .lib.utils import make_block
from .lib import utils


class GithubHandler(GithubToken, HasOutput, HasStructure):

    @staticmethod
    def define_arguments(argument_parser):
        argument_parser.add_argument('--event', '-e', dest='event', metavar="GITHUB_EVENT",
                                     help='Currently parsed from "x-github-event" header of received web-hook')
        argument_parser.add_argument('--payload', '-pl', dest='payload', metavar="GITHUB_PAYLOAD",
                                     help='Full contents of web-hook received; leave "-" to redirect to stdin '
                                          'or pass a JSON file path, starting it with "@" character')
        argument_parser.add_argument('--trigger-url', '-tu', dest='trigger_url', metavar="TRIGGER_URL",
                                     help='URL for GET request to trigger the CI build and pass all parameters '
                                          'parsed from payload; if any constant parameters (like token) are '
                                          'requiered, include them in this string as well, e.g.: '
                                          '"http://jenkins.com/job/JobName/build?token=MYTOKEN"')
        argument_parser.add_argument('--suite-name', '-sn', dest='suite_name', metavar="SUITE_NAME", default="CI tests",
                                     help='GitHub check suite name, default is "CI tests"')
        argument_parser.add_argument('--target-repo', '-tr', dest='target_repo', metavar="TARGET_REPO",
                                     help='Repository name to process; leave blank to process any repo')
        argument_parser.add_argument('--verbose', '-v', dest='verbose', action="store_true",
                                     help='Show all params passed in URL (mostly for debug purposes)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        utils.check_required_option(self.settings, "event", """
                    GitHub web-hook event is not specified.

                    Please pass 'X-GitHub-Event' header contents of incoming web-hook request via command line
                    parameter '--event' ('-e') or GITHUB_EVENT environment variable.
                """)
        utils.check_required_option(self.settings, "trigger_url", """
                    CI build trigger URL is not specified.

                    Trigger URL is a string to be extended by parsed build parameters and used in a GET request
                    to start a CI build that can report a GitHub build check.
                    For example, 'http://jenkins.com/job/JobName/build?token=MYTOKEN'
                    
                    Please specify this parameter by using '--trigger-url' ('-tu')
                    command line parameter or by setting TRIGGER_URL environment variable.
                """)
        self.payload = utils.read_and_check_multiline_option(self.settings, "payload", """
                    GitHub web-hook payload JSON is not specified.

                    Please pass incoming web-hook request payload to this parameter directly via '--payload' ('-pl')
                    command line parameter or by setting GITHUB_PAYLOAD environment variable, or by passing file path
                    as the argument value (start filename with '@' character, e.g. '@/tmp/file.json' or '@payload.json'
                    for relative path starting at current directory), or via stdin (leave '-' valuer for redirection).
                """)

    @make_block("Analysing trigger payload")
    def execute(self):
        try:
            payload = json.loads(self.payload)
        except json.decoder.JSONDecodeError as error:
            text = f"Provided payload value could not been parsed as JSON and returned the following error:\n {error}"
            raise CriticalCiException(text) from error

        try:
            if self.settings.target_repo:
                parsed_repo = payload['repository']['full_name']
                if parsed_repo != self.settings.target_repo:
                    text = f"This payload has come from '{parsed_repo}' repository, while due to parameter passed to "
                    text += f" '--target-repo' only '{self.settings.target_repo}' repository is handled. Skipping..."
                    self.out.log(text)
                    return

            if self.settings.event == "check_suite" and (payload["action"] in ["requested", "rerequested"]):
                url = payload["repository"]["url"] + "/check-runs"
                data = {"name": self.settings.suite_name, "head_sha": payload["check_suite"]["head_sha"]}
                headers = {'Authorization': f"token {self.get_token(payload['installation']['id'])}",
                           'Accept': 'application/vnd.github.antiope-preview+json'}
                self.out.log(f"Sending request to {url}")
                if self.settings.verbose:
                    self.out.log(f"Headers are:\n{headers}\nOther passed params are:\n{data}")
                utils.make_request(url=url, request_method="POST", json=data, headers=headers)
                self.out.log("Successfully created check run")

            elif self.settings.event == "check_run" and \
                    (payload["action"] in ["requested", "rerequested", "created"]) and \
                    (str(payload["check_run"]["app"]["id"]) == str(self.settings.integration_id)):
                param_dict = {
                    "GIT_REFSPEC": payload["check_run"]["check_suite"]["head_branch"],
                    "GIT_CHECKOUT_ID": payload["check_run"]["head_sha"],
                    "GITHUB_CHECK_ID": payload["check_run"]["id"],
                    "GIT_REPO": payload["repository"]["clone_url"],
                    "GITHUB_INSTALLATION_ID": payload["installation"]["id"]
                }
                self.out.log(f"Triggering {urllib.parse.urljoin(self.settings.trigger_url, '?...')}")
                response = utils.make_request(self.settings.trigger_url, params=param_dict)
                if self.settings.verbose:
                    self.out.log(f"Triggered {response.url}")
                else:
                    self.out.log("Successfully triggered")

            else:
                self.out.log("Unhandled event, skipping...")
        except KeyError as error:
            raise CriticalCiException(f"Could not find key {error} in provided payload:\n{payload}") from error
        except TypeError as error:
            raise CriticalCiException("Parsed payload JSON does not correspond to expected format") from error

    def finalize(self):
        pass
