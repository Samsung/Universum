"""
    Declare all base classes for further implementation
"""
import shutil

from .ci_exception import CiException
from .gravity import Module
from .utils import make_block

__all__ = [
    "OutputBase",
    "AutomationServerDriverBase",
    "VcsBase"
]


class OutputBase(Module):
    """
    Abstract base class for output modules.
    """

    def open_block(self, num_str, name):
        raise NotImplementedError

    def close_block(self, num_str, name, status):
        raise NotImplementedError

    def report_error(self, description):
        raise NotImplementedError

    def report_skipped(self, message):
        raise NotImplementedError

    def change_status(self, message):
        raise NotImplementedError

    def log_exception(self, line):
        raise NotImplementedError

    def log_stderr(self, line):
        raise NotImplementedError

    def log(self, line):
        raise NotImplementedError

    def log_external_command(self, command):
        raise NotImplementedError

    def log_shell_output(self, line):
        raise NotImplementedError


class AutomationServerDriverBase(Module):
    """
    Abstract base class for API of automation (CI) server
    """

    def trigger_build(self, revision):  # pylint: disable=no-self-use
        raise RuntimeError("Trigger build function is not defined for current driver.")

    def report_build_location(self):
        raise NotImplementedError

    def artifact_path(self, local_artifacts_dir, item):
        raise NotImplementedError


class VcsBase(Module):
    def __init__(self, settings, project_root):
        super(VcsBase, self).__init__()
        self.settings = settings
        self.project_root = project_root
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
        Create new change, add all reconciled files to index and submit to repository
        :param description: Change description
        :param file_list: List of full paths to files to be submitted
        :param review: When set to True, create deletable review instead of submit
        :param add_new: When set to True, add to submit files not yet present in repository
        :return: Created change number
        """
        raise NotImplementedError

    def prepare_repository(self):
        raise NotImplementedError

    @make_block("Cleaning copied sources")
    def clean_sources(self):
        try:
            shutil.rmtree(self.project_root)
        except OSError as e:
            text = unicode(e) + "\nPossible reasons of this error:" + \
                   "\n * Sources were not copied due to runtime errors" + \
                   "\n * Copied sources are already deleted while executing generated scenario" + \
                   "\n * Source files permissions do not allow deleting"
            raise CiException(text)

    def finalize(self):
        if self.sources_need_cleaning:
            self.clean_sources()
