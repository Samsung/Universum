# -*- coding: UTF-8 -*-

import os
import pickle
import tempfile

from ..lib.gravity import Module

__all__ = [
    "ApiSupport"
]


class ApiSupport(Module):
    def __init__(self, api_mode=False, **kwargs):
        super(ApiSupport, self).__init__(**kwargs)

        if api_mode:
            if "UNIVERSUM_DATA_FILE" not in os.environ:
                raise EnvironmentError("Error: Failed to read the 'UNIVERSUM_DATA_FILE' from environment")
            with open(os.getenv("UNIVERSUM_DATA_FILE"), "rb+") as data_file:
                self.data = pickle.load(data_file)
        else:
            self.data_file = tempfile.NamedTemporaryFile(mode="wb+")
            self.data = {}

    def _set_entry(self, name, entry):
        self.data[name] = entry

    def _get_entry(self, name):
        return self.data.get(name, "")

    def get_environment_settings(self):
        pickle.dump(self.data, self.data_file)
        self.data_file.flush()
        return {"UNIVERSUM_DATA_FILE": self.data_file.name}

    def add_file_diff(self, entry):
        self._set_entry("DIFF", entry)

    def get_file_diff(self):
        return self._get_entry("DIFF")
