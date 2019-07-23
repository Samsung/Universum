# -*- coding: UTF-8 -*-

import sys

from .modules.api_support import ApiSupport
from .lib.gravity import Module, Dependency
from .lib.utils import format_traceback

__all__ = ["Api"]


class Api(Module):
    description = "Universum API"
    api_support_factory = Dependency(ApiSupport)

    @staticmethod
    def define_arguments(parser):
        parser.add_argument('action', choices=["get-shelves", "file-diff", "swarm"],
                            help="Input some description")

    def __init__(self, *args, **kwargs):
        super(Api, self).__init__(*args, **kwargs)
        try:
            self.api_support = self.api_support_factory(api_mode=True)
        except EnvironmentError as error:
            sys.stderr.write(unicode(error) + u"\n")
            sys.exit(2)

        class MinimalOut(object):
            @staticmethod
            def log(line):
                pass

            @staticmethod
            def report_build_problem(problem):
                pass

            @staticmethod
            def log_exception(error):
                ex_traceback = sys.exc_info()[2]
                sys.stderr.write("Unexpected error.\n" + format_traceback(error, ex_traceback))

        self.out = MinimalOut()

    def execute(self):
        if self.settings.action == "file-diff":
            print self.api_support.get_file_diff()
        else:
            raise NotImplementedError()

    def finalize(self):
        pass
