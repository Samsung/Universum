import os

from universum.modules.launcher import Launcher


class Nonci(Launcher):

    def __init__(self, *args, **kwargs):
        # Patch settings before parent class is initialized
        if not self.settings.output:
            self.settings.output = 'console'

        if not self.settings.project_root:
            self.settings.project_root = os.getcwd()

        super().__init__(*args, **kwargs)

    def execute(self):
        self.out.log("Cleaning artifacts...")
        self.artifact_collector.clean_artifacts_silently()

        project_configs = self.process_project_configs()
        self.code_report_collector.prepare_environment(project_configs)
        self.artifact_collector.set_and_clean_artifacts(project_configs, ignore_existing_artifacts=True)

        self.launch_project()
        self.reporter.report_initialized = True
        self.artifact_collector.report_artifacts()
        self.reporter.report_build_result()

    def finalize(self):
        pass
