#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys

from _universum import artifact_collector, file_manager, launcher, reporter
from _universum import utils, __title__, __version__
from _universum.entry_points import run_main_for_module, run_with_settings, setup_arg_parser
from _universum.gravity import Module, Dependency
from _universum.output import needs_output


@needs_output
class Main(Module):
    description = __title__
    files_factory = Dependency(file_manager.FileManager)
    launcher_factory = Dependency(launcher.Launcher)
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)
    reporter_factory = Dependency(reporter.Reporter)

    @staticmethod
    def define_arguments(parser):
        parser.add_argument("--version", action="version", version=__title__ + " " + __version__)

        parser.add_hidden_argument("--no-finalize", action="store_true", dest="no_finalize", is_hidden=True,
                                   help="Skip 'Finalizing' step: "
                                        "do not clear sources, do not revert workspace files, etc. "
                                        "Is applied automatically when using existing VCS client")

        parser.add_hidden_argument("--finalize-only", action="store_true", dest="finalize_only", is_hidden=True,
                                   help="Perform only 'Finalizing' step: clear sources, revert workspace files, etc. "
                                        "Recommended to use after '--no-finalize' runs. "
                                        "Please make sure to move artifacts from working directory "
                                        "or pass different artifact folder")

    def __init__(self):
        self.files = self.files_factory()
        self.project_root = self.files.project_root
        self.launcher = self.launcher_factory(self.project_root)
        self.artifacts = self.artifacts_factory()
        self.reporter = self.reporter_factory()

    def execute(self):
        if self.settings.finalize_only:
            self.files.vcs.sources_need_cleaning = True
            self.out.log("Execution skipped because of '--finalize-only' option")
            return

        self.files.prepare_repository()
        project_configs = self.launcher.process_project_configs()

        artifact_list = []
        report_artifact_list = []
        for configuration in project_configs.all():
            if "artifacts" in configuration:
                path = utils.parse_path(configuration["artifacts"], self.project_root)
                clean = configuration.get("artifact_prebuild_clean", False)
                artifact_list.append(dict(path=path, clean=clean))
            if "report_artifacts" in configuration:
                path = utils.parse_path(configuration["report_artifacts"], self.project_root)
                clean = configuration.get("artifact_prebuild_clean", False)
                report_artifact_list.append(dict(path=path, clean=clean))

        if artifact_list:
            self.artifacts.set_and_clean_artifacts(artifact_list)
        if report_artifact_list:
            self.artifacts.set_and_clean_report_artifacts(report_artifact_list)

        self.reporter.report_build_started()
        self.launcher.launch_project()
        self.artifacts.collect_artifacts()
        self.reporter.report_build_result()

    def finalize(self):
        if self.settings.no_finalize:
            self.out.log("Cleaning skipped because of '--no-finalize' option")
            return
        self.files.finalize()


def define_arguments():
    return setup_arg_parser(Main)


def run(settings):
    return run_with_settings(Main, settings)


def main(*args, **kwargs):
    return run_main_for_module(Main, *args, **kwargs)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
