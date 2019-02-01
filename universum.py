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


def define_arguments(*args):
    parser = ModuleArgumentParser(description=__title__ + " " + __version__)
    parser.add_argument("--version", action="version", version=__title__ + " " + __version__)
    define_arguments_recursive(Main, parser)

    subparsers = parser.add_subparsers(title="Additional commands",
                                       metavar="{poll,submit}",
                                       help="Use 'universum <subcommand> --help' for more info")
    define_arguments_recursive(Api, subparsers.add_parser("api"))
    define_arguments_recursive(Poll, subparsers.add_parser("poll"))
    define_arguments_recursive(Submit, subparsers.add_parser("submit"))

    if parser.needs_default_parser(*args):
        default_parser = "default"
        subparsers.add_parser(default_parser)
        if args:
            args[0].insert(len(args), default_parser)
        else:
            sys.argv.insert(len(sys.argv), default_parser)

    return parser


def run(settings):
    result = 0
    main_module = construct_component(settings.main_class, settings)

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


def main(*args, **kwargs):
    parser = define_arguments(*args)
    settings = parser.parse_args(*args, **kwargs)
    settings.main_class = getattr(settings, "main_class", Main)
    try:
        return run(settings)
    except IncorrectParameterError as e:
        parser.error(e.message)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
