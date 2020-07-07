import signal
import sys

from . import __version__, __title__
from .api import Api
from .main import Main
from .github_handler import GithubHandler
from .nonci import Nonci
from .poll import Poll
from .submit import Submit
from .lib.ci_exception import SilentAbortException
from .lib.gravity import define_arguments_recursive, construct_component
from .lib.module_arguments import ModuleArgumentParser, IncorrectParameterError
from .lib.utils import Uninterruptible, format_traceback


def define_arguments():
    parser = ModuleArgumentParser(prog="python3.7 -m universum",
                                  description=__title__ + " " + __version__)
    parser.add_argument("--version", action="version", version=__title__ + " " + __version__)
    define_arguments_recursive(Main, parser)

    subparsers = parser.add_subparsers(title="Additional commands",
                                       metavar="{poll,submit,nonci,github-handler}",
                                       help="Use 'universum <subcommand> --help' for more info")

    def define_command(klass, command):
        command_parser = subparsers.add_parser(command)
        command_parser.set_defaults(command_parser=command_parser)
        command_parser.set_defaults(main_class=klass)
        define_arguments_recursive(klass, command_parser)

    define_command(Api, "api")
    define_command(Poll, "poll")
    define_command(Submit, "submit")
    define_command(Nonci, "nonci")
    define_command(GithubHandler, "github-handler")

    return parser


def run(settings):
    result = 0
    main_module = construct_component(settings.main_class, settings)
    main_module.out.log("{} {} started execution".format(__title__, __version__))

    def signal_handler(signal_number, stack_frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)

    try:
        with Uninterruptible(main_module.out.log_exception) as run_function:
            run_function(main_module.execute)
            run_function(main_module.finalize)

    except SilentAbortException as e:
        result = e.application_exit_code

    except Exception as e:
        ex_traceback = sys.exc_info()[2]
        main_module.out.log_exception("Unexpected error.\n" + format_traceback(e, ex_traceback))
        main_module.out.report_build_problem("Unexpected error while executing script.")
        result = 2

    main_module.out.log("{} {} finished execution".format(__title__, __version__))
    return result


def main(args=None):
    parser = define_arguments()
    settings = parser.parse_args(args)
    settings.main_class = getattr(settings, "main_class", Main)
    settings.command_parser = getattr(settings, "command_parser", parser)

    try:
        return run(settings)
    except IncorrectParameterError as e:
        settings.command_parser.error(e)
    except ImportError as e:
        print(e)
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
