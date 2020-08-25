from typing import ClassVar
from . import __title__
from .lib.ci_exception import SilentAbortException
from .lib.gravity import Dependency
from .lib.module_arguments import ModuleArgumentParser
from .modules import vcs, artifact_collector, reporter, launcher, code_report_collector
from .modules.output import HasOutput


__all__ = ["Main"]


class Main(HasOutput):
    description: ClassVar[str] = __title__
    vcs_factory: ClassVar = Dependency(vcs.MainVcs)
    launcher_factory: ClassVar = Dependency(launcher.Launcher)
    artifacts_factory: ClassVar = Dependency(artifact_collector.ArtifactCollector)
    reporter_factory: ClassVar = Dependency(reporter.Reporter)
    code_report_collector_factory: ClassVar = Dependency(code_report_collector.CodeReportCollector)

    @staticmethod
    def define_arguments(argument_parser: ModuleArgumentParser) -> None:
        argument_parser.add_hidden_argument("--no-finalize", action="store_true", dest="no_finalize",
                                            help="Skip 'Finalizing' step: "
                                                 "do not clear sources, do not revert workspace vcs, etc. "
                                                 "Is applied automatically when using existing VCS client")

        argument_parser.add_hidden_argument("--finalize-only", action="store_true", dest="finalize_only",
                                            help="Perform only 'Finalizing' step: "
                                                 "clear sources, revert workspace vcs, etc. "
                                                 "Recommended to use after '--no-finalize' runs. "
                                                 "Please make sure to move artifacts from working directory "
                                                 "or pass different artifact folder")

        argument_parser.add_hidden_argument("--clean-build", action="store_true", dest="clean_build",
                                            help="Clean artifact and build directory before build "
                                                 "instead of raising exception. Not recommended for CI configurations!")

        argument_parser.add_argument("--build-only-latest", action="store_true", dest="build_only_latest",
                                     help="Skip build if review version isn't latest")
        argument_parser.add_argument("--no-diff", action="store_true", dest="no_diff",
                                     help="Only applies to build steps where ``code_report=True``; "
                                          "disables calculating analysis diff for changed files, "
                                          "in this case full analysis report will be published")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vcs: vcs.MainVcs = self.vcs_factory()
        self.launcher: launcher.Launcher = self.launcher_factory()
        self.artifacts: artifact_collector.ArtifactCollector = self.artifacts_factory()
        self.reporter: reporter.Reporter = self.reporter_factory()
        self.code_report_collector: code_report_collector.CodeReportCollector = self.code_report_collector_factory()

    def execute(self) -> None:
        if self.settings.clean_build:
            self.vcs.clean_sources_silently()
            self.artifacts.clean_artifacts_silently()

        if self.settings.finalize_only:
            self.vcs.driver.sources_need_cleaning = True
            self.out.log("Execution skipped because of '--finalize-only' option")
            return

        self.reporter.report_review_link()
        if self.settings.build_only_latest:
            if not self.vcs.is_latest_review_version():
                self.out.log("Build skipped because review revision is not latest")
                self.out.report_build_status("Skipped - review revision is not latest")
                raise SilentAbortException(application_exit_code=0)

        self.vcs.prepare_repository()
        project_configs = self.launcher.process_project_configs()
        afterall_configs = self.code_report_collector.prepare_environment(project_configs)
        self.artifacts.set_and_clean_artifacts(project_configs)

        self.reporter.report_build_started()
        self.launcher.launch_project()
        if afterall_configs:
            if not self.settings.no_diff:
                try:
                    repo_diff = self.vcs.revert_repository()
                except NotImplementedError:
                    self.out.log("Diff calculation for code report is skipped because current VCS doesn't support it")
                else:
                    self.launcher.launch_custom_configs(afterall_configs)
                    self.code_report_collector.repo_diff = repo_diff
            self.code_report_collector.report_code_report_results()
        self.artifacts.collect_artifacts()
        self.reporter.report_build_result()

    def finalize(self) -> None:
        if self.settings.no_finalize:
            self.out.log("Cleaning skipped because of '--no-finalize' option")
            return
        self.vcs.finalize()
