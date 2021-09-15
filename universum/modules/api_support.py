from typing import Dict, Union
import inspect
import os
import sys
import pickle
import tempfile

from ..lib.gravity import Module
from ..lib.ci_exception import SilentAbortException

__all__ = [
    "ApiSupport"
]


class ApiSupport(Module):
    def __init__(self, api_mode: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)

        if api_mode:
            if "UNIVERSUM_DATA_FILE" not in os.environ:
                raise EnvironmentError(
                    inspect.cleandoc("""Error: Failed to read the 'UNIVERSUM_DATA_FILE' from environment
                
                    This command is intended to be run from within Universum run (e.g. as a separate step
                    in project config file). If you got this message by running it from command line:
                    please don't. If you got this message by running it with Universum: something must
                    have gone wrong, may be a bug in Universum itself. Feel free to contact the developers."""))

            with open(os.getenv("UNIVERSUM_DATA_FILE", ""), "rb+") as data_file:
                self.data = pickle.load(data_file)
        else:
            self.data_file = tempfile.NamedTemporaryFile(mode="wb+")  # pylint: disable = consider-using-with
            self.data = {}

    def _set_entry(self, name: str, entry: Union[str, bool]) -> None:
        self.data[name] = entry

    def _get_entry(self, name: str) -> str:
        return self.data.get(name, "")

    def get_environment_settings(self) -> Dict[str, str]:
        pickle.dump(self.data, self.data_file)
        self.data_file.flush()
        return {"UNIVERSUM_DATA_FILE": self.data_file.name}

    def add_file_diff(self, entry: Union[str, None]) -> None:
        if entry is None:
            self._set_entry("DIFF_FAILED", True)
        else:
            self._set_entry("DIFF", entry)

    def get_file_diff(self) -> str:
        if self._get_entry("DIFF_FAILED") is True:
            sys.stderr.write("Getting file diff failed due to Perforce server internal error")
            raise SilentAbortException(application_exit_code=1)
        return self._get_entry("DIFF")
