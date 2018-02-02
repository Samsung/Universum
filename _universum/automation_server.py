# -*- coding: UTF-8 -*-

import urllib2

from .ci_exception import CriticalCiException
from .base_classes import AutomationServerBase
from .output import needs_output


@needs_output
class BasicServer(AutomationServerBase):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Automation server", "Basic automation server options")
        parser.add_argument('--url', '-u', dest='url',
                            help='Url to trigger, must include exactly one conversion specifier (%%s) to be '
                                 'replaced by CL number, for example: http://localhost/%%s', required=True, metavar="URL")

    def __init__(self, settings):
        self.settings = settings

    def trigger_build(self, revision):

        processed_url = self.settings.url % revision

        self.out.log("Triggering url %s" % processed_url)
        try:
            urllib2.urlopen(processed_url)
        except urllib2.URLError as url_error:
            raise CriticalCiException("Error opening URL, error message " + unicode(url_error.reason))
        except ValueError as value_error:
            raise CriticalCiException("Error opening URL, error message " + unicode(value_error))

        return True

AutomationServer = BasicServer
