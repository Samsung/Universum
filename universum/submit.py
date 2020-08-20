from .lib import utils
from .lib.gravity import Module, Dependency
from .lib.module_arguments import IncorrectParameterError
from .lib.utils import make_block
from .modules import vcs
from .modules.output import HasOutput
from .modules.structure_handler import needs_structure

__all__ = ["Submit"]


@needs_structure
class Submit(HasOutput, Module):
    description = "Submitting module of Universum"
    vcs_factory = Dependency(vcs.SubmitVcs)

    @staticmethod
    def define_arguments(parser):
        parser.add_argument("--create-review", action="store_true", dest="review",
                            help="create deletable review (shelve for P4, temp branch for Git) "
                                 "instead of actual submitting to repo")
        parser.add_argument("--edit-only", action="store_true", dest="edit_only",
                            help="Only submit existing vcs modifications, no adding or deleting")

        parser.add_argument('--commit-message', '-cm', dest='commit_message', metavar="COMMIT_MESSAGE",
                            help='Commit message to add')
        parser.add_argument("--reconcile-list", "-rl", action="append", nargs='+', dest="reconcile_list",
                            metavar="RECONCILE_LIST",
                            help="List of vcs or directories to be reconciled for commit. "
                                 "Relative paths starting at client root are supported")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        if not getattr(self.settings, "commit_message", None):
            raise IncorrectParameterError("commit message is not specified.\n\n"
                                          "Please use '--commit-message' option or COMMIT_MESSAGE\n"
                                          "environment variable")

        self.vcs = self.vcs_factory()
        self.client = None

    @make_block("Executing")
    def execute(self):
        path_list = utils.unify_argument_list(self.settings.reconcile_list)
        change = self.vcs.driver.submit_new_change(self.settings.commit_message,
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
        self.vcs.finalize()
