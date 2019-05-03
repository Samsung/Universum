# -*- coding: UTF-8 -*-

import os
import shutil

from ...lib.ci_exception import CriticalCiException
from ...lib.module_arguments import IncorrectParameterError
from ...lib.utils import make_block
from ...lib import utils
from ..output import needs_output
from ..structure_handler import needs_structure
from . import base_vcs

__all__ = [
    "LocalMainVcs"
]


@needs_output
@needs_structure
class LocalMainVcs(base_vcs.BaseDownloadVcs):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Local files",
                                                     "Parameters for file settings in case of no VCS used")

        parser.add_argument('--file-source-dir', '-fsd', dest="source_dir", metavar='SOURCE_DIR',
                            help="A local folder for project sources to be copied from. "
                                 "This option is only needed when '--driver-type' is set to 'none'")

    def __init__(self, *args, **kwargs):
        super(LocalMainVcs, self).__init__(*args, **kwargs)

        if not getattr(self.settings, "source_dir", None):
            raise IncorrectParameterError("the source directory is not specified.\n"
                                          "Please specify source directory by using --file-source-dir\n"
                                          "command-line option or SOURCE_DIR environment variable")
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
            text = unicode(e) + "\nPossible reasons of this error:"
            text += "\n * Sources path, passed to the script ('" + self.settings.source_dir + \
                    "'), does not lead to actual sources or was processed incorrectly"
            text += "\n * Directory '" + os.path.basename(self.settings.project_root) + \
                    "' already exists in working dir (e.g. due to previous builds)"
            text += "\n * File reading permissions troubles"
            raise CriticalCiException(text)
