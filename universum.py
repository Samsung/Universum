#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from _universum import artifact_collector, file_manager, launcher, reporter
from _universum import utils, __title__, __version__
from _universum.entry_points import run_main_for_module, setup_arg_parser
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

    def __init__(self):
        self.files = self.files_factory()
        self.project_root = self.files.project_root
        self.launcher = self.launcher_factory(self.project_root)
        self.artifacts = self.artifacts_factory()
        self.reporter = self.reporter_factory()

    def execute(self):
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
            self.out.run_in_block(self.artifacts.set_and_clean_artifacts,
                                  "Setting and preprocessing artifacts according to configs", True, artifact_list)
        if report_artifact_list:
            self.out.run_in_block(self.artifacts.set_and_clean_report_artifacts,
                                  "Setting and preprocessing artifacts to be mentioned in report", True, report_artifact_list)

        self.reporter.report_build_started()
        self.launcher.launch_project()
        self.artifacts.collect_artifacts()
        self.reporter.report_build_result()

    def finalize(self):
        self.files.finalize()


def define_arguments():
    return setup_arg_parser(Main)


def main(*args, **kwargs):
    return run_main_for_module(Main, *args, **kwargs)


if __name__ == "__main__":
    main()
