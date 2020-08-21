import os
import shutil

from ..error_state import HasErrorState
from ...lib.ci_exception import CriticalCiException
from ...lib.utils import make_block
from ...lib import utils
from ..output import HasOutput
from ..structure_handler import HasStructure
from . import base_vcs

__all__ = [
    "LocalMainVcs"
]


class LocalMainVcs(base_vcs.BaseDownloadVcs, HasOutput, HasStructure, HasErrorState):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Local files",
                                                     "Parameters for file settings in case of no VCS used")

        parser.add_argument('--file-source-dir', '-fsd', dest="source_dir", metavar='SOURCE_DIR',
                            help="A local folder for project sources to be copied from. "
                                 "This option is only needed when '--driver-type' is set to 'none'")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not getattr(self.settings, "source_dir", None):
            self.error("""The source directory is not specified.
            
                          The source directory defines the location of the project sources on a local
                          filesystem.
            
                          Please specify source directory by using --file-source-dir
                          command-line option or SOURCE_DIR environment variable.""")
        else:
            self.source_dir = utils.parse_path(self.settings.source_dir, os.getcwd())

    def calculate_file_diff(self):  # pylint: disable=no-self-use
        return {}                   # No file diff can be calculated for local VCS

    @make_block("Copying sources to working directory")
    def prepare_repository(self):
        self.sources_need_cleaning = True        # pylint: disable=attribute-defined-outside-init
        try:
            self.out.log("Moving sources to '" + self.settings.project_root + "'...")
            shutil.copytree(self.source_dir, self.settings.project_root)
            self.append_repo_status("Got sources from: " + self.source_dir + "\n")
        except OSError as e:
            text = f"{e}\nPossible reasons of this error:"
            text += f"\n * Sources path, passed to the script ('{self.settings.source_dir}')," + \
                    " does not lead to actual sources or was processed incorrectly"
            text += "\n * Directory '{}' already exists in working dir (e.g. due to previous builds)".format(
                os.path.basename(self.settings.project_root))
            text += "\n * File reading permissions troubles"
            raise CriticalCiException(text) from e
