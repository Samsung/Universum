from pathlib import Path
import sys

from .modules.output.output import MinimalOut
from .lib.gravity import Module
__all__ = ["ConfigCreator"]

PYTHON_VERSION = f"python{sys.version_info.major}.{sys.version_info.minor}"


class ConfigCreator(Module):
    description: str = "Create a dummy project"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.out = MinimalOut()

    def execute(self) -> None:
        config_name = ".universum.py"
        self.out.log(f"Creating an example configuration file '{config_name}'")

        config = Path(config_name)
        config.write_text("""#!/usr/bin/env {}

from universum.configuration_support import Configuration

configs = Configuration([dict(name='Show directory contents', command=['ls', '-la']),
                      dict(name='Print a line', command=['bash', '-c', 'echo Hello world'])])

if __name__ == '__main__':
    print(configs.dump())
""".format(PYTHON_VERSION))
        self.out.log(f"To run with Universum, execute the following command:\n$ {PYTHON_VERSION} -m universum run")

    def finalize(self) -> None:
        pass
