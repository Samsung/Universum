from pathlib import Path

from .modules.output.output import MinimalOut
from .lib.gravity import Module
__all__ = ["ProjectInitializer"]


class ProjectInitializer(Module):
    description: str = "Create a dummy project"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.out = MinimalOut()

    def execute(self) -> None:
        target_dir = "universum_dummy_project"
        target_dir_path = Path(target_dir)
        script_name = "dummy_script.sh"
        config_name = "universum_config.py"
        artifact_name = "artifact_example.txt"
        self.out.log("Creating a dummy project in " + target_dir)
        target_dir_path.mkdir(parents=True, exist_ok=True)

        script = target_dir_path / script_name
        script.write_text("""#!/usr/bin/env bash
echo "This is an example of a build artifact.\\n" > {}
echo "Replace this script with actual project sources"
""".format(artifact_name))
        script.chmod(0o777)

        config = target_dir_path / config_name
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
                     " --artifact-dir={}`".format(target_dir, config_name, "universum_artifacts"))

    def finalize(self) -> None:
        pass
