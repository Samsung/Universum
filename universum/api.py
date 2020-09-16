import sys

from .modules.api_support import ApiSupport
from .modules.output.output import MinimalOut
from .lib.gravity import Module, Dependency
from .lib.module_arguments import ModuleArgumentParser

__all__ = ["Api"]


class Api(Module):
    description: str = "Universum API"
    api_support_factory = Dependency(ApiSupport)

    @staticmethod
    def define_arguments(parser: ModuleArgumentParser) -> None:
        parser.add_argument('action', choices=["get-shelves", "file-diff", "swarm"],
                            help="Input some description")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        try:
            self.api_support: ApiSupport = self.api_support_factory(api_mode=True)
        except EnvironmentError as error:
            sys.stderr.write(str(error) + '\n')
            sys.exit(2)

        self.out = MinimalOut(silent=True)

    def execute(self) -> None:
        if self.settings.action == "file-diff":
            print(self.api_support.get_file_diff())
        else:
            raise NotImplementedError()

    def finalize(self) -> None:
        pass
