# -*- coding: UTF-8 -*-

import os
import urllib2

from .base_server import BaseServer
from ..ci_exception import CriticalCiException
from ..module_arguments import IncorrectParameterError
from ..output import needs_output

__all__ = [
    "JenkinsServer"
]


@needs_output
class JenkinsServer(BaseServer):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Jenkins variables", "Jenkins-specific parameters")
        parser.add_argument("--jenkins-build-url", "-jbu", dest="build_url", metavar="BUILD_URL",
                            help="Link to build on Jenkins (automatically set by Jenkins)")
        parser.add_argument('--jenkins-trigger-url', '-jtu', dest='trigger_url',
                            help='Url to trigger, must include exactly one conversion specifier (%%s) to be '
                                 'replaced by CL number, for example: http://localhost/%%s', metavar="URL")

    def check_required_option(self, name):
        if getattr(self.settings, name) is None:
            raise IncorrectParameterError("Unable to retrieve Jenkins variable '" + name + "'")

    def trigger_build(self, revision):
        self.check_required_option('trigger_url')
        processed_url = self.settings.trigger_url % revision

        self.out.log("Triggering url %s" % processed_url)
        try:
            urllib2.urlopen(processed_url)
        except urllib2.URLError as url_error:
            raise CriticalCiException("Error opening URL, error message " + unicode(url_error.reason))
        except ValueError as value_error:
            raise CriticalCiException("Error opening URL, error message " + unicode(value_error))

        return True

    def report_build_location(self):
        self.check_required_option('build_url')
        log_link = self.settings.build_url + "console"
        return "Here is the link to build log on Jenkins: " + log_link

    def artifact_path(self, local_artifacts_dir, item):
        self.check_required_option('build_url')
        artifact_link = self.settings.build_url + "artifact/" + \
                        os.path.relpath(local_artifacts_dir, os.getcwd()) + "/"
        return artifact_link + item
