#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import json

from _universum.gravity import Module, Dependency
from _universum import automation_server, file_manager
from _universum.utils import make_block
from _universum.output import needs_output
from _universum.entry_points import run_main_for_module, run_with_settings


@needs_output
class Poller(Module):
    description = "Polling module of Universum "
    files_factory = Dependency(file_manager.FileManager)
    server_factory = Dependency(automation_server.AutomationServer)

    @staticmethod
    def define_arguments(parser):
        parser.add_argument('--file', '-f', dest='db_file', help='File to store last known CLs', default="p4poll.json")
        parser.add_argument('--num', '-n', dest='max_number', help='Maximum number of CLs processed, default is 10',
                            type=int, default=10)

    def __init__(self, settings):
        self.settings = settings
        self.stored_cls = {}
        self.latest_cls = {}
        self.triggered_cls = set()

        self.files = self.files_factory()
        self.server = self.server_factory()

    def process_single_mapping(self, depot):
        if len(self.latest_cls[depot]) == 1:
            self.stored_cls[depot] = self.latest_cls[depot].pop()
            self.out.log("No changes detected")
            return

        for change in self.latest_cls[depot]:
            if change != self.stored_cls[depot]:
                if change in self.triggered_cls:
                    self.out.log("Commit {} already processed".format(change))
                    continue

                self.out.log("Detected commit {}, triggering build".format(change))
                if self.server.trigger_build(change):
                    self.triggered_cls.add(change)
                    if self.stored_cls[depot] < change:
                        self.stored_cls[depot] = change
            else:
                self.out.log("Commit {} already processed".format(change))

    @make_block("Enumerating changes")
    def execute(self):
        try:
            with open(self.settings.db_file) as db_file:
                self.stored_cls = json.load(db_file)
        except IOError as io_error:
            if io_error.errno == 2:
                pass
            else:
                raise

        try:
            self.latest_cls = self.files.vcs.get_changes(self.stored_cls, self.settings.max_number)
            for depot in self.latest_cls.keys():
                self.out.run_in_block(self.process_single_mapping, "Processing depot " + depot, True, depot)
        finally:
            with open(self.settings.db_file, "w") as db_file:
                json.dump(self.stored_cls, db_file, indent=4, sort_keys=True)

    def finalize(self):
        self.files.finalize()


def run(settings):
    return run_with_settings(Poller, settings)


def main(*args, **kwargs):
    return run_main_for_module(Poller, *args, **kwargs)


if __name__ == "__main__":
    main()
