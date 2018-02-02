# -*- coding: UTF-8 -*-

import os
import shutil

import sh

from . import base_classes, gerrit_vcs, git_vcs, perforce_vcs, artifact_collector, utils
from .gravity import Module, Dependency
from .ci_exception import CriticalCiException
from .utils import make_block
from .output import needs_output
from .module_arguments import IncorrectParameterError

__all__ = [
    "LocalVcs",
    "FileManager"
]


@needs_output
class LocalVcs(base_classes.VcsBase):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Local files",
                                                     "Parameters for file settings in case of no VCS used")

        parser.add_argument('--files-source-dir', '-fsd', dest="source_dir", metavar='SOURCE_DIR',
                            help="A local folder for project sources to be copied from. "
                                 "This option is only needed when '--vcs-type' is set to 'none'")

    def __init__(self, settings, project_root, report_to_review):
        super(LocalVcs, self).__init__(settings, project_root)

        if self.settings.source_dir is None:
            raise IncorrectParameterError("Please specify source directory if not using any VCS")
        if report_to_review:
            raise IncorrectParameterError("You requested posting report to code review, "
                                          "but selected local file system as VCS."
                                          "There is no code review associated with local files.")

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


@needs_output
class FileManager(Module):
    local_vcs_factory = Dependency(LocalVcs)
    git_vcs_factory = Dependency(git_vcs.GitVcs)
    gerrit_vcs_factory = Dependency(gerrit_vcs.GerritVcs)
    perforce_vcs_factory = Dependency(perforce_vcs.PerforceVcs)
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)

    # TODO: remove hide_sync_options and add_hidden_argument

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Source files",
                                                     "Parameters determining the processing of repository files")

        parser.add_argument("--vcs-type", "-vt", dest="vcs", default="p4",
                            choices=["none", "p4", "git", "gerrit"],
                            help="Select repository type to download sources from: "
                                 "Perforce ('p4', the default), Git ('git'), Gerrit ('gerrit') or a local directory ('none'). "
                                 "Gerrit uses Git parameters. "
                                 "Each VCS type has its own settings.")

        parser.add_argument("--project-root", "-pr", dest="project_root", metavar="PROJECT_ROOT",
                            help="Temporary directory to copy sources to. Default is 'temp'")

        parser.add_hidden_argument("--no-finalize", action="store_true", dest="no_finalize", is_hidden=True,
                                   help="Skip 'Finalizing' step: do not clear sources, do not revert workspace files. "
                                        "Is applied automatically when using existing VCS client")

        parser.add_argument("--report-to-review", action="store_true", dest="report_to_review", default=False,
                            help="Perform test build for code review system (e.g. Gerrit or Swarm).")

    def __init__(self, settings):
        self.settings = settings
        self.artifacts = None

        self.project_root = settings.project_root
        if not self.project_root:
            self.project_root = os.path.join(os.getcwd(), "temp")

        if self.settings.vcs == "none":
            self.vcs = self.local_vcs_factory(self.project_root, settings.report_to_review)
        elif self.settings.vcs == "git":
            self.vcs = self.git_vcs_factory(self.project_root, settings.report_to_review)
        elif self.settings.vcs == "gerrit":
            self.vcs = self.gerrit_vcs_factory(self.project_root, settings.report_to_review)
        else:
            self.vcs = self.perforce_vcs_factory(self.project_root, settings.report_to_review)

    @make_block("Preparing repository")
    def prepare_repository(self):
        self.artifacts = self.artifacts_factory()
        status_file = self.artifacts.create_text_file("REPOSITORY_STATE.txt")

        self.vcs.prepare_repository()

        status_file.write(self.vcs.get_repo_status())

        status_file.write("\nFile list:\n\n")
        status_file.write(utils.trim_and_convert_to_unicode(sh.ls("-lR", self.project_root)) + "\n")
        status_file.close()

    @make_block("Finalizing")
    def finalize(self):
        if self.settings.no_finalize:
            self.out.log("Skipped because of '--no-finalize' option")
            return
        self.vcs.finalize()
