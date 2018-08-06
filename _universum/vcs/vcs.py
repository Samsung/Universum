# -*- coding: UTF-8 -*-

import os
import sh

from . import git_vcs, gerrit_vcs, perforce_vcs, local_vcs
from .. import artifact_collector, utils
from ..gravity import Module, Dependency
from ..output import needs_output
from ..structure_handler import needs_structure
from ..utils import make_block

__all__ = [
    "Vcs"
]


@needs_output
@needs_structure
class Vcs(Module):
    local_driver_factory = Dependency(local_vcs.LocalVcs)
    git_driver_factory = Dependency(git_vcs.GitVcs)
    gerrit_driver_factory = Dependency(gerrit_vcs.GerritVcs)
    perforce_driver_factory = Dependency(perforce_vcs.PerforceVcs)
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)

    # TODO: remove hide_sync_options and add_hidden_argument

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Source vcs",
                                                     "Parameters determining the processing of repository vcs")

        parser.add_argument("--vcs-type", "-vt", dest="type", default="p4",
                            choices=["none", "p4", "git", "gerrit"],
                            help="Select repository type to download sources from: Perforce ('p4', the default), "
                                 "Git ('git'), Gerrit ('gerrit') or a local directory ('none'). "
                                 "Gerrit uses Git parameters. Each VCS type has its own settings.")

        parser.add_argument("--project-root", "-pr", dest="project_root", metavar="PROJECT_ROOT",
                            help="Temporary directory to copy sources to. Default is 'temp'")

        parser.add_argument("--report-to-review", action="store_true", dest="report_to_review", default=False,
                            help="Perform test build for code review system (e.g. Gerrit or Swarm).")

    def __init__(self, *args, **kwargs):
        super(Vcs, self).__init__(*args, **kwargs)
        self.artifacts = None

        self.project_root = self.settings.project_root
        if not self.project_root:
            self.project_root = os.path.join(os.getcwd(), "temp")

        args = [self.project_root, self.settings.report_to_review]
        if self.settings.type == "none":
            self.driver = self.local_driver_factory(*args)
        elif self.settings.type == "git":
            self.driver = self.git_driver_factory(*args)
        elif self.settings.type == "gerrit":
            self.driver = self.gerrit_driver_factory(*args)
        else:
            self.driver = self.perforce_driver_factory(*args)

    @make_block("Preparing repository")
    def prepare_repository(self):
        self.artifacts = self.artifacts_factory()
        status_file = self.artifacts.create_text_file("REPOSITORY_STATE.txt")

        self.driver.prepare_repository()

        status_file.write(self.driver.get_repo_status())

        status_file.write("\nFile list:\n\n")
        status_file.write(utils.trim_and_convert_to_unicode(sh.ls("-lR", self.project_root)) + "\n")
        status_file.close()

    @make_block("Finalizing")
    def finalize(self):
        self.driver.finalize()
