from .lib import utils
from .lib.gravity import Dependency
from .lib.utils import make_block
from .modules import vcs
from .modules.error_state import HasErrorState
from .modules.output import HasOutput
from .modules.structure_handler import HasStructure

__all__ = ["Submit"]


class Submit(HasOutput, HasStructure, HasErrorState):
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
                            help="Commit message. Enter in command line directly, store in environment variable "
                                 "or pass a file path to read the message from by starting the value string with "
                                 "'@'. File path can be either absolute or relative. "
                                 "Please note, that when passing a file, it is expected to be in UTF-8 encoding")
        parser.add_argument("--reconcile-list", "-rl", dest="reconcile_list", metavar="RECONCILE_LIST",
                            help="Comma-separated or linebreak-separated list of files or directories "
                                 "to be reconciled for commit (relative paths starting at client root "
                                 "are supported). To use command line directly, add quotes if needed "
                                 "(e.g. ``-rl 'target1, target2'``). To use a file with reconcile list, "
                                 "start a path to file with '@' (e.g. ``-rl @/path/to/file``)."
                                 "Please note, that when passing a file, it's expected to be in UTF-8 "
                                 "encoding")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.commit_message = self.read_and_check_multiline_option("commit_message", """
            Commit message is not specified.

            Please use '--commit-message' option to provide it. If you start the parameter with '@', the
            rest should be the path to a file containing the commit message text. The path can be absolute
            or relative to the project root. You can also store the message in COMMIT_MESSAGE environment variable.
            Please note, that when passing a file, it's expected to be in UTF-8 encoding
            """)

        try:
            self.reconcile_list = utils.unify_argument_list(self.read_multiline_option("reconcile_list").splitlines())
        except AttributeError:
            self.reconcile_list = []

        self.vcs = self.vcs_factory()
        self.client = None

    @make_block("Executing")
    def execute(self):
        change = self.vcs.driver.submit_new_change(self.commit_message,
                                                   self.reconcile_list,
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
