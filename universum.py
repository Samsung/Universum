#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

import atexit
import signal
import sys

from _universum import __version__, __title__
from _universum.api import Api
from _universum.main import Main
from _universum.poll import Poll
from _universum.submit import Submit
from _universum.lib.ci_exception import SilentAbortException
from _universum.lib.gravity import define_arguments_recursive, construct_component
from _universum.lib.module_arguments import ModuleArgumentParser, IncorrectParameterError
from _universum.lib.utils import Uninterruptible, format_traceback


def define_arguments():
    parser = ModuleArgumentParser(description=__title__ + " " + __version__)
    parser.add_argument("--version", action="version", version=__title__ + " " + __version__)
    define_arguments_recursive(Main, parser)

    subparsers = parser.add_subparsers(title="Additional commands",
                                       metavar="{poll,submit}",
                                       help="Use 'universum <subcommand> --help' for more info")

    def define_command(klass, command):
        command_parser = subparsers.add_parser(command)
        command_parser.set_defaults(command_parser=command_parser)
        command_parser.set_defaults(main_class=klass)
        define_arguments_recursive(klass, command_parser)

    define_command(Api, "api")
    define_command(Poll, "poll")
    define_command(Submit, "submit")

    return parser


def run(settings):
    result = 0
    main_module = construct_component(settings.main_class, settings)
    main_module.out.log("Running {} {}".format(__title__, __version__))

    finalized = False

    def finalize():
        if not finalized:
            main_module.finalize()

    try:
        with Uninterruptible(main_module.out.log_exception) as run_function:
            run_function(main_module.execute)
            run_function(main_module.finalize)
            finalized = True

    except SilentAbortException as e:
        result = e.application_exit_code

    except Exception as e:
        ex_traceback = sys.exc_info()[2]
        main_module.out.log_exception("Unexpected error.\n" + format_traceback(e, ex_traceback))
        main_module.out.report_build_problem("Unexpected error while executing script.")
        result = 2

    atexit.register(finalize)
    signal.signal(signal.SIGTERM, finalize)
    signal.signal(signal.SIGHUP, finalize)
    signal.signal(signal.SIGINT, finalize)

    return result


def main(args=None):
    parser = define_arguments()
    settings = parser.parse_args(args)
    settings.main_class = getattr(settings, "main_class", Main)
    settings.command_parser = getattr(settings, "command_parser", parser)

    try:
        return run(settings)
    except IncorrectParameterError as e:
        settings.command_parser.error(e.message)
    except ImportError as e:
        print unicode(e)
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
