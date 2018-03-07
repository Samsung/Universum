import sys

from . import __version__
from .ci_exception import SilentAbortException
from .gravity import construct_component, define_arguments_recursive
from .module_arguments import ModuleArgumentParser, IncorrectParameterError
from .utils import Uninterruptible, format_traceback


def run_with_settings(main_class, settings):
    result = 0

    main = construct_component(main_class, settings)

    try:
        with Uninterruptible() as run:
            run(main.execute)
            run(main.finalize)
    except SilentAbortException as e:
        result = e.application_exit_code

    except Exception as e:
        ex_traceback = sys.exc_info()[2]
        main.out.log_exception("Unexpected error.\n" + format_traceback(e, ex_traceback))
        main.out.report_build_problem("Unexpected error while executing script.")
        result = 2

    return result


def setup_arg_parser(main_class):
    parser = ModuleArgumentParser(description=main_class.description + " " + __version__)
    define_arguments_recursive(main_class, parser)
    return parser


def run_main_for_module(main_class, *args, **kwargs):
    parser = setup_arg_parser(main_class)
    settings = parser.parse_args(*args, **kwargs)

    try:
        return run_with_settings(main_class, settings)
    except IncorrectParameterError as e:
        parser.error(e.message)
