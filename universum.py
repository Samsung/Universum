#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import atexit
import signal
import sys

from _universum import __version__, __title__
from _universum.main import Main
from _universum.poll import Poll
from _universum.submit import Submit
from _universum.lib.ci_exception import SilentAbortException
from _universum.lib.gravity import define_arguments_recursive, construct_component
from _universum.lib.module_arguments import ModuleArgumentParser, IncorrectParameterError
from _universum.lib.utils import Uninterruptible, format_traceback


def define_arguments(main_class=Main):
    if main_class is Main:
        epilog = "Available subcommands are 'poll' and 'submit'. Use 'universum <subcommand> --help' for more info"
    else:
        epilog = None
    parser = ModuleArgumentParser(description=__title__ + " " + __version__, epilog=epilog)
    parser.add_argument("--version", action="version", version=__title__ + " " + __version__)

    define_arguments_recursive(main_class, parser)
    return parser


def run(main_class, settings):
    result = 0

    main_module = construct_component(main_class, settings)

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
    command = None
    # 'command' may or may not be the first positional argument for this script
    # if no command is passed to script, default 'Main' module is executed
    # if any command is passed, it chould be parsed and excluded from parameters before calling argparse
    # because argparse should parse different arguments depending on 'command' value
    try:
        # if main is called from another python script, *args and **kwargs are passed to arparse
        # args is a tuple of up to three elements, where first one is a list of passed arguments
        # if any 'command' is passed to main this way, it should be the first element of args[0]
        if not args[0][0].startswith("-"):
            command = args[0][0]
            # if succeeded, removing command parameter from immutable tuple 'args':
            arg_list = list(args)
            arg_list[0] = args[0][1:]
            args = tuple(arg_list)
    except IndexError:
        # IndexError means no parameters were passed via *args
        # so we should check sys.argv for 'command'
        try:
            if not sys.argv[1].startswith("-"):
                command = sys.argv[1]
                # and also remove 'command' from parameters passed to argparse if succeeded
                sys.argv.pop(1)
        except IndexError:
            # if no parameters were passed via *args or sys.argv, argparse will handle this situation
            pass

    if command == "submit":
        main_class = Submit
    elif command == "poll":
        main_class = Poll
    else:
        main_class = Main
    parser = define_arguments(main_class)
    settings = parser.parse_args(*args, **kwargs)
    try:
        return run(main_class, settings)
    except IncorrectParameterError as e:
        parser.error(e.message)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
