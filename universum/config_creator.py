from pathlib import Path

from .modules.output.output import MinimalOut
from .lib.gravity import Module
__all__ = ["ConfigCreator"]


class ConfigCreator(Module):
    description: str = "Create a dummy project"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.out = MinimalOut()

    def execute(self) -> None:
        config_name = ".universum.py"
        self.out.log(f"Creating an example configuration file '{config_name}'")

        config = Path(config_name)
        config.write_text("""#!/usr/bin/env python3.7

from universum.configuration_support import Variations

configs = Variations([dict(name='Show directory contents', command=['ls', '-la']),
                      dict(name='Print a line', command=['bash', '-c', 'echo Hello world'])])

if __name__ == '__main__':
    print(configs.dump())
""")
        self.out.log("To run with Universum, execute the following command:\n"
                     "$ python3.7 -m universum nonci".format(config_name))

    def finalize(self) -> None:
        pass
