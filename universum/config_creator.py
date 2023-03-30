import pathlib
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

        config = pathlib.Path(config_name)
        config.write_text(f"""#!/usr/bin/env {PYTHON_VERSION}

from universum.configuration_support import Configuration, Step

configs = Configuration([Step(name='Show directory contents', command=['ls', '-la']),
                         Step(name='Print a line', command=['bash', '-c', 'echo Hello world'])])

if __name__ == '__main__':
    print(configs.dump())
""", encoding="utf-8")
        self.out.log(f"To run with Universum, execute the following command:\n$ {PYTHON_VERSION} -m universum run")

    def finalize(self) -> None:
        pass
