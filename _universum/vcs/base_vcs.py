# -*- coding: UTF-8 -*-

import shutil

from ..ci_exception import CiException
from ..module_arguments import IncorrectParameterError
from ..project_directory import ProjectDirectory
from ..utils import make_block

__all__ = [
    "BaseVcs"
]


class BaseVcs(ProjectDirectory):
    """
    Base class for VCS drivers
    """

    @staticmethod
    def define_arguments(argument_parser):
        pass

    def code_review(self):  # pylint: disable=no-self-use
        raise IncorrectParameterError("There is no code review system associated with this VCS type")

    def __init__(self, *args, **kwargs):
        super(BaseVcs, self).__init__(*args, **kwargs)
        self.repo_status = u""
        self.sources_need_cleaning = False

    def append_repo_status(self, line):
        self.repo_status += line

    def get_repo_status(self):
        return self.repo_status

    def get_changes(self, changes_reference=None, max_number='1'):
        """
        Get all (or last 'max_number' for a depot path) changes starting from reference state
        :param changes_reference: Dictionary, where keys are depot paths and values are latest known changes
        :param max_number: Maximum number of changes for every depot path to return
        :return: Dictionary, where keys are depot paths and values are sets of changes
        """
        raise NotImplementedError

    def submit_new_change(self, description, file_list, review=False, edit_only=False):
        """
        Create new change, add all reconciled vcs to index and submit to repository
        :param description: Change description
        :param file_list: List of full paths to vcs to be submitted
        :param review: When set to True, create deletable review instead of submit
        :param add_new: When set to True, add to submit vcs not yet present in repository
        :return: Created change number
        """
        raise NotImplementedError

    def prepare_repository(self):
        raise NotImplementedError

    @make_block("Cleaning copied sources")
    def clean_sources(self):
        try:
            shutil.rmtree(self.settings.project_root)
        except OSError as e:
            text = unicode(e) + "\nPossible reasons of this error:" + \
                   "\n * Sources were not copied due to runtime errors" + \
                   "\n * Copied sources are already deleted while executing generated scenario" + \
                   "\n * Source vcs permissions do not allow deleting"
            raise CiException(text)

    def finalize(self):
        if self.sources_need_cleaning:
            self.clean_sources()
