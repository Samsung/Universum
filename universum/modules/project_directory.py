import os

from ..lib import utils
from ..lib.gravity import Module


class ProjectDirectory(Module):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Source files",
                                                     "Parameters determining the processing of repository files")

        parser.add_argument("--project-root", "-pr", dest="project_root", metavar="PROJECT_ROOT",
                            help="Temporary directory to copy sources to. Default is 'temp'")

    def __init__(self, *args, **kwargs):
        if self.settings.project_root:
            self.settings.project_root = utils.parse_path(self.settings.project_root, os.getcwd())
        else:
            self.settings.project_root = os.path.join(os.getcwd(), "temp")
        super().__init__(*args, **kwargs)
