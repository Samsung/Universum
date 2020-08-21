import os

from ...lib.module_arguments import IncorrectParameterError
from ...lib import utils
from ..output import HasOutput
from .base_server import BaseServerForHostingBuild, BaseServerForTrigger

__all__ = [
    "JenkinsServerForTrigger",
    "JenkinsServerForHostingBuild"
]


class JenkinsServerForTrigger(HasOutput, BaseServerForTrigger):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Jenkins variables", "Jenkins-specific parameters")
        parser.add_argument('--jenkins-trigger-url', '-jtu', dest='trigger_url',
                            help='Url to trigger, must include exactly one conversion specifier (%%s) to be '
                                 'replaced by CL number, for example: http://localhost/%%s', metavar="URL")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not getattr(self.settings, "trigger_url", None):
            raise IncorrectParameterError("the Jenkins url for triggering build\n"
                                          "is not specified\n\n"
                                          "Please specify the url by using '--jenkins-trigger-url' ('-jtu')\n"
                                          "command-line option or URL environment variable.")

    def trigger_build(self, revision):
        processed_url = self.settings.trigger_url % revision
        self.out.log("Triggering url %s" % processed_url)
        utils.make_request(processed_url)


class JenkinsServerForHostingBuild(BaseServerForHostingBuild):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Jenkins variables", "Jenkins-specific parameters")
        parser.add_argument("--jenkins-build-url", "-jbu", dest="build_url", metavar="BUILD_URL",
                            help="Link to build on Jenkins (automatically set by Jenkins)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
