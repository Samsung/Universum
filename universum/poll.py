import json

from .lib.gravity import Dependency
from .lib.utils import make_block
from .modules import automation_server, vcs
from .modules.output import HasOutput
from .modules.structure_handler import HasStructure

__all__ = ["Poll"]


class Poll(HasOutput, HasStructure):
    description = "Polling module of Universum"
    vcs_factory = Dependency(vcs.PollVcs)
    server_factory = Dependency(automation_server.AutomationServerForTrigger)

    @staticmethod
    def define_arguments(parser):
        parser.add_argument('--file', '-f', dest='db_file', metavar="DB_FILE",
                            help='File to store last known CLs', default="p4poll.json")
        parser.add_argument('--num', '-n', dest='max_number', metavar="MAX_NUMBER",
                            help='Maximum number of CLs processed, default is 10', type=int, default=10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stored_cls = {}
        self.latest_cls = {}
        self.triggered_cls = set()

        self.vcs = self.vcs_factory()
        self.server = self.server_factory()

    def process_single_mapping(self, depot):
        if len(self.latest_cls[depot]) == 1:
            self.stored_cls[depot] = self.latest_cls[depot].pop()
            self.out.log("No changes detected")
            return

        for change in self.latest_cls[depot]:
            if change == self.stored_cls[depot]:
                self.out.log("Commit {} is latest known".format(change))
                continue

            if change in self.triggered_cls:
                self.out.log("Commit {} already processed".format(change))
                continue

            self.out.log("Detected commit {}, triggering build".format(change))
            self.server.trigger_build(change)
            self.triggered_cls.add(change)
            self.stored_cls[depot] = change

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
            self.latest_cls = self.vcs.driver.get_changes(self.stored_cls, self.settings.max_number)
            for depot in self.latest_cls.keys():
                self.structure.run_in_block(self.process_single_mapping, "Processing depot " + depot, True, depot)
        except NotImplementedError:
            self.out.log("Polling is skipped because current VCS doesn't support it")
        finally:
            with open(self.settings.db_file, "w") as db_file:
                json.dump(self.stored_cls, db_file, indent=4, sort_keys=True)

    def finalize(self):
        self.vcs.finalize()
