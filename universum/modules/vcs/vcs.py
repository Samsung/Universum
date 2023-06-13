from typing import Dict, List, Optional, TextIO, Tuple, Type, Union
import json
import shutil
import sh

from . import git_vcs, github_app_vcs, gerrit_vcs, github_actions_vcs, perforce_vcs, local_vcs, base_vcs
from .. import artifact_collector
from ..api_support import ApiSupport
from ..error_state import HasErrorState
from ..project_directory import ProjectDirectory
from ..structure_handler import HasStructure
from ...lib import utils
from ...lib.gravity import Dependency
from ...lib.utils import make_block

__all__ = [
    "MainVcs",
    "PollVcs",
    "SubmitVcs"
]


def create_vcs(class_type: Optional[str] = None) -> Type[ProjectDirectory]:
    driver_factory_class: Union[
        Dict[str, Type[base_vcs.BasePollVcs]],
        Dict[str, Type[base_vcs.BaseSubmitVcs]],
        Dict[str, Type[base_vcs.BaseDownloadVcs]]
    ]
    if class_type == "submit":
        driver_factory_class = {
            "none": base_vcs.BaseSubmitVcs,
            "p4": perforce_vcs.PerforceSubmitVcs,
            "git": git_vcs.GitSubmitVcs,
            "gerrit": gerrit_vcs.GerritSubmitVcs,
            "ghapp": git_vcs.GitSubmitVcs,
            "ghactions": git_vcs.GitSubmitVcs
        }
    elif class_type == "poll":
        driver_factory_class = {
            "none": base_vcs.BasePollVcs,
            "p4": perforce_vcs.PerforcePollVcs,
            "git": git_vcs.GitPollVcs,
            "gerrit": git_vcs.GitPollVcs,
            "ghapp": git_vcs.GitPollVcs,
            "ghactions": git_vcs.GitPollVcs
        }
    else:
        driver_factory_class = {
            "none": local_vcs.LocalMainVcs,
            "p4": perforce_vcs.PerforceMainVcs,
            "git": git_vcs.GitMainVcs,
            "gerrit": gerrit_vcs.GerritMainVcs,
            "ghapp": github_app_vcs.GithubAppMainVcs,
            "ghactions": github_actions_vcs.GithubActionsMainVcs
        }

    vcs_types: List[str] = ["none", "p4", "git", "gerrit", "ghapp", "ghactions"]

    class Vcs(ProjectDirectory, HasStructure, HasErrorState):
        local_driver_factory = Dependency(driver_factory_class['none'])
        git_driver_factory = Dependency(driver_factory_class['git'])
        gerrit_driver_factory = Dependency(driver_factory_class['gerrit'])
        ghapp_driver_factory = Dependency(driver_factory_class['ghapp'])
        ghactions_driver_factory = Dependency(driver_factory_class['ghactions'])
        perforce_driver_factory = Dependency(driver_factory_class['p4'])

        @staticmethod
        def define_arguments(argument_parser):
            parser = argument_parser.get_or_create_group("Source files")

            parser.add_argument("--vcs-type", "-vt", dest="type",
                                choices=vcs_types, metavar="VCS_TYPE",
                                help="Select repository type to download sources from: Perforce ('p4'), "
                                     "Git ('git'), Gerrit ('gerrit'), GitHub App ('ghapp'), "
                                     "GitHub Actions ('ghactions'), or a local directory ('none'). "
                                     "Gerrit uses Git parameters. Each VCS type has its own settings.")

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            if not getattr(self.settings, "type", None):
                self.error(f"""
                    The repository (VCS) type is not set.
                     
                    The repository type defines the version control system that is used for
                    performing the requested action. For example, Universum needs to get project
                    source codes for performing Continuous Integration (CI) builds.

                    The following types are supported: {', '.join(vcs_types)}.
                    
                    Each of these types requires supplying its own
                    configuration parameters. At the minimum, the following
                    parameters are required:
                      * "git", "ghapp", "ghactions" and "gerrit" - GIT_REPO (-gr) and GIT_REFSPEC (-grs)
                      * "perforce"                               - P4PORT (-p4p), P4USER (-p4u), P4PASSWD (-p4P)
                      * "none"                                   - SOURCE_DIR (-fsd)
                      
                    Depending on the requested action, additional type-specific parameters are
                    required. For example, P4CLIENT (-p4c) is required for CI builds with perforce.
                    
                    Please specify the VCS type by using '--vcs-type' ('-vt') command-line option or
                    VCS_TYPE environment variable.
                    """)
                return

            if self.settings.type == "none":
                driver_factory = self.local_driver_factory
            elif self.settings.type == "git":
                driver_factory = self.git_driver_factory
            elif self.settings.type == "gerrit":
                driver_factory = self.gerrit_driver_factory
            elif self.settings.type == "ghapp":
                driver_factory = self.ghapp_driver_factory
            elif self.settings.type == "ghactions":
                driver_factory = self.ghactions_driver_factory
            else:
                driver_factory = self.perforce_driver_factory

            self.driver = driver_factory()

        @make_block("Finalizing")
        def finalize(self):
            self.driver.finalize()

    return Vcs


PollVcs: Type[ProjectDirectory] = create_vcs("poll")
SubmitVcs: Type[ProjectDirectory] = create_vcs("submit")


class MainVcs(create_vcs()):  # type: ignore  # https://github.com/python/mypy/issues/2477
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)
    api_support_factory = Dependency(ApiSupport)
    driver: base_vcs.BaseDownloadVcs

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Source files")

        parser.add_argument("--report-to-review", action="store_true", dest="report_to_review", default=False,
                            help="Perform test build for code review system (e.g. Gerrit or Swarm).")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.artifacts: artifact_collector.ArtifactCollector = self.artifacts_factory()
        self.api_support: ApiSupport = self.api_support_factory()

        if not self.settings.report_to_review:
            return

        if not getattr(self, "driver", None):
            return

        self.code_review = self.driver.code_review()
        if not self.code_review:
            self.error("""
                There is no code review system associated with current VCS type, but reporting
                to the code review system is requested.
                
                If the reporting to the code review system is requested, the universum updates
                the review request based on the build status. However, the currently chosen VCS
                doesn't have associated code review system.
                
                Please either disable reporting to the code review system by removing
                '--report-to-review' command-line parameter or change the VCS type by using
                '--vcs-type' ('-vt') command-line option or VCS_TYPE environment variable
                """)

    def login(self):
        self.driver.login()

    def is_latest_review_version(self):
        if self.settings.report_to_review:
            return self.code_review.is_latest_version()
        return True

    @make_block("Preparing repository")
    def prepare_repository(self) -> None:
        status_file: TextIO = self.artifacts.create_text_file("REPOSITORY_STATE.txt")

        try:
            self.driver.prepare_repository()
        finally:
            status_file.write(self.driver.get_repo_status())
            try:
                sources_list = utils.trim_and_convert_to_unicode(sh.ls("-lR", self.settings.project_root))
                status_file.write(f"\n\nFile list:\n{sources_list}\n")
            except sh.ErrorReturnCode_2 as e:
                if "No such file or directory" not in str(e):
                    raise
            status_file.close()

        self.calculate_diff_for_api()

    @make_block("Registering file diff for API")
    def calculate_diff_for_api(self) -> None:
        file_diff = self.driver.calculate_file_diff()
        if file_diff is not None:
            file_diff = json.dumps(file_diff, indent=4)
        self.api_support.add_file_diff(file_diff)

    def clean_sources_silently(self):
        try:
            shutil.rmtree(self.settings.project_root)
        except OSError:
            pass

    @make_block("Revert repository")
    def revert_repository(self) -> Optional[List[Tuple[Optional[str], Optional[str], Optional[str]]]]:
        diff = self.driver.copy_cl_files_and_revert()
        return diff
