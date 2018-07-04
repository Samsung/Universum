#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys

from _universum import file_manager, utils
from _universum.entry_points import run_main_for_module, run_with_settings
from _universum.gravity import Module, Dependency
from _universum.module_arguments import IncorrectParameterError
from _universum.output import needs_output
from _universum.structure_handler import needs_structure
from _universum.perforce_vcs import catch_p4exception
from _universum.utils import make_block


@needs_output
@needs_structure
class Submit(Module):
    description = "Submitting module of Universum "
    files_factory = Dependency(file_manager.FileManager)

    @staticmethod
    def define_arguments(parser):
        parser.add_argument("--create-review", action="store_true", dest="review",
                            help="create deletable review (shelve for P4, temp branch for Git) "
                                 "instead of actual submitting to repo")
        parser.add_argument("--edit-only", action="store_true", dest="edit_only",
                            help="Only submit existing files modifications, no adding or deleting")

        parser.add_argument('--commit-message', '-cm', dest='commit_message', metavar="COMMIT_MESSAGE",
                            help='Commit message to add')
        parser.add_argument("--reconcile-list", "-rl", action="append", nargs='+', dest="reconcile_list",
                            metavar="RECONCILE_LIST",
                            help="List of files or directories to be reconciled for commit. "
                                 "Relative paths starting at client root are supported")

    def __init__(self):
        if getattr(self.settings, "commit_message") is None:
            raise IncorrectParameterError("Commit message is required. Please use '--commit-message' option "
                                          "or COMMIT_MESSAGE environment variable")

        self.files = self.files_factory()
        self.client = None

    @make_block("Executing")
    @catch_p4exception()
    def execute(self):
        path_list = utils.unify_argument_list(self.settings.reconcile_list)
        change = self.files.vcs.submit_new_change(self.settings.commit_message,
                                                  path_list,
                                                  review=self.settings.review,
                                                  edit_only=self.settings.edit_only)

        if change == 0:
            self.out.log("Nothing to submit")
        elif self.settings.review:
            self.out.log("Review commit " + change + " created")
        else:
            self.out.log("Change " + change + " submitted")

    @make_block("Finalizing", pass_errors=False)
    def finalize(self):
        self.files.vcs.finalize()


def run(settings):
    return run_with_settings(Submit, settings)


def main(*args, **kwargs):
    return run_main_for_module(Submit, *args, **kwargs)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
