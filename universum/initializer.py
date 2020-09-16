from pathlib import Path

from .modules.output.output import MinimalOut
from .lib.gravity import Module
from .lib.module_arguments import ModuleArgumentParser

__all__ = ["Initializer"]


class Initializer(Module):
    description: str = "Create a dummy project"

    @staticmethod
    def define_arguments(parser: ModuleArgumentParser) -> None:
        parser.add_argument('--target-direcotry', '-td', dest='target_dir', metavar="TARGET_DIRECTORY",
                            help='Desired directory to put a dummy project to')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.settings.target_dir:
            self.target_dir = Path("universum_dummy_project")
        else:
            self.target_dir = Path(self.settings.target_dir)
        self.target_dir_str = str(self.target_dir)

        self.out = MinimalOut()

    def execute(self) -> None:
        script_name = "dummy_script.sh"
        config_name = "universum_config.py"
        artifact_name = "artifact_example.txt"
        self.out.log("Creating a dummy project in " + self.target_dir_str)
        self.target_dir.mkdir(parents=True, exist_ok=True)

        script = self.target_dir / script_name
        script.write_text("""#!/usr/bin/env bash
echo "This is an example of a build artifact.\\n" > {}
echo "Replace this script with actual project sources"
""".format(artifact_name))
        script.chmod(0o777)

        config = self.target_dir / config_name
        config.write_text("""#!/usr/bin/env python3.7

from universum.configuration_support import Variations

configs = Variations([dict(name='Show directory contents', command=['ls', '-la']),
                      dict(name='Run dummy script', command=['{}'], artifacts='{}')])

if __name__ == '__main__':
    print(configs.dump())
""".format(script_name, artifact_name))

        self.out.log("Dummy project created.")
        self.out.log("To run with Universum, execute the following command:\n"
                     "`python3.7 -m universum --vcs-type=none --file-source-dir={} --launcher-config-path={}"
                     " --artifact-dir={}`".format(self.target_dir_str, config_name, "universum_artifacts"))

    def finalize(self) -> None:
        pass
