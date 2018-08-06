import os
import shutil

from .base_vcs import BaseVcs
from ..ci_exception import CriticalCiException
from ..module_arguments import IncorrectParameterError
from ..output import needs_output
from ..structure_handler import needs_structure
from ..utils import make_block
from .. import utils


@needs_output
@needs_structure
class LocalVcs(BaseVcs):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Local vcs",
                                                     "Parameters for file settings in case of no VCS used")

        parser.add_argument('--vcs-source-dir', '-fsd', dest="source_dir", metavar='SOURCE_DIR',
                            help="A local folder for project sources to be copied from. "
                                 "This option is only needed when '--driver-type' is set to 'none'")

    def __init__(self, project_root, report_to_review):
        super(LocalVcs, self).__init__(project_root)

        if self.settings.source_dir is None:
            raise IncorrectParameterError("Please specify source directory if not using any VCS")
        if report_to_review:
            raise IncorrectParameterError("You requested posting report to code review, "
                                          "but selected local file system as VCS."
                                          "There is no code review associated with local vcs.")

        self.source_dir = utils.parse_path(self.settings.source_dir, os.getcwd())

    def get_changes(self, changes_reference=None, max_number='1'):
        raise NotImplementedError

    def submit_new_change(self, description, file_list, review=False, edit_only=False):
        raise NotImplementedError

    @make_block("Copying sources to working directory")
    def prepare_repository(self):
        self.sources_need_cleaning = True
        try:
            self.out.log("Moving sources to '" + self.project_root + "'...")
            shutil.copytree(self.source_dir, self.project_root)
            self.append_repo_status("Got sources from: " + self.source_dir + "\n")
        except OSError as e:
            text = unicode(e) + "\nPossible reasons of this error:"
            text += "\n * Sources path, passed to the script ('" + self.settings.source_dir + \
                    "'), does not lead to actual sources or was processed incorrectly"
            text += "\n * Directory '" + os.path.basename(self.project_root) + \
                    "' already exists in working dir (e.g. due to previous builds)"
            text += "\n * File reading permissions troubles"
            raise CriticalCiException(text)
