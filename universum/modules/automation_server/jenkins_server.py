import copy
import os
import requests
import urllib.parse

from ...lib.ci_exception import CriticalCiException
from ...lib.module_arguments import IncorrectParameterError
from ...lib.utils import unify_argument_list
from ..output import needs_output
from .base_server import BaseServerForHostingBuild, BaseServerForTrigger

__all__ = [
    "JenkinsServerForTrigger",
    "JenkinsServerForHostingBuild"
]


@needs_output
class JenkinsServerForTrigger(BaseServerForTrigger):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Jenkins variables", "Jenkins-specific parameters")
        parser.add_argument('--jenkins-trigger-url', '-jtu', dest='trigger_url', metavar="TRIGGER_URL",
                            help='Url to trigger, ending with "build" or "buildWithParameters" accordingly')
        parser.add_argument('--jenkins-trigger-parameter', "-jtp", action="append", nargs='+', dest="param_list",
                            metavar="TRIGGER_PARAMS",
                            help="List of parameters to pass to Jenkins build, such as token; "
                                 "format 'name=value', case sensitive")

    def __init__(self, *args, **kwargs):
        super(JenkinsServerForTrigger, self).__init__(*args, **kwargs)
        if not getattr(self.settings, "trigger_url", None):
            raise IncorrectParameterError("the Jenkins url for triggering build\n"
                                          "is not specified\n\n"
                                          "Please specify the url by using '--jenkins-trigger-url' ('-jtu')\n"
                                          "command-line option or URL environment variable.")
        self.params = unify_argument_list(self.settings.param_list)

    def trigger_build(self, param_dict=None):
        processed_url = self.settings.trigger_url
        if param_dict:
            self.params.append(urllib.parse.urlencode(param_dict))
        if self.params:
            processed_url += '?' + '&'.join(self.params)

        self.out.log(f"Triggering url {processed_url}")
        try:
            response = requests.post(processed_url)
            response.raise_for_status()
            self.out.log("Sucessfully triggered")
        except (requests.HTTPError, requests.ConnectionError, ValueError) as e:
            raise CriticalCiException(f"Error opening URL, error message {e}")


class JenkinsServerForHostingBuild(BaseServerForHostingBuild):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Jenkins variables", "Jenkins-specific parameters")
        parser.add_argument("--jenkins-build-url", "-jbu", dest="build_url", metavar="BUILD_URL",
                            help="Link to build on Jenkins (automatically set by Jenkins)")

    def __init__(self, *args, **kwargs):
        super(JenkinsServerForHostingBuild, self).__init__(*args, **kwargs)
        if not getattr(self.settings, "build_url", None):
            raise IncorrectParameterError("the Jenkins url of the ongoing build\n"
                                          "is not specified\n\n"
                                          "Please specify the url by using '--jenkins-build-url' ('-jbu')\n"
                                          "command-line option or BUILD_URL environment variable.")

    def report_build_location(self):
        log_link = self.settings.build_url + "console"
        return "Here is the link to build log on Jenkins: " + log_link

    def artifact_path(self, local_artifacts_dir, item):
        artifact_link = self.settings.build_url + "artifact/" + \
                        os.path.relpath(local_artifacts_dir, os.getcwd()) + "/"
        return artifact_link + item
