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
        self.artifacts.clean_artifacts_silently()

        project_configs = self.process_project_configs()
        self.artifacts.set_and_clean_artifacts(project_configs, ignore_existing_artifacts=True)

        self.launch_project()
        self.reporter.report_initialized = True
        self.reporter.report_build_result()
        self.artifacts.collect_artifacts()

    def finalize(self):
        pass
