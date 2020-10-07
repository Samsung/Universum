from typing import cast, Callable, Dict, List, Optional, TextIO, Tuple
from types import ModuleType

import importlib
import os
import shutil
import warnings

import sh

from ..error_state import HasErrorState
from ...modules.artifact_collector import ArtifactCollector
from ...modules.reporter import Reporter
from ...lib.ci_exception import CriticalCiException, SilentAbortException
from ...lib.gravity import Dependency
from ...lib.utils import make_block, Uninterruptible, convert_to_str
from ...lib import utils
from ..output import HasOutput
from ..structure_handler import HasStructure
from . import base_vcs
from .swarm import Swarm

__all__ = [
    "PerforceMainVcs",
    "PerforcePollVcs",
    "PerforceSubmitVcs",
    "catch_p4exception"
]

P4Exception = None


class P4stub(ModuleType):  # replace with proper stubs
    P4Exception: Exception
    P4: Callable


def catch_p4exception(ignore_if=None):
    return utils.catch_exception("P4Exception", ignore_if)


class PerforceVcs(base_vcs.BaseVcs, HasOutput, HasStructure, HasErrorState):
    """
    This class contains global functions for interaction with Perforce
    """

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Perforce",
                                                     "Please read the details about P4 environment variables "
                                                     "in official Helix manual")

        parser.add_argument("--p4-port", "-p4p", dest="port", help="P4 port (e.g. 'myhost.net:1666')", metavar="P4PORT")
        parser.add_argument("--p4-user", "-p4u", dest="user", help="P4 user name", metavar="P4USER")
        parser.add_argument("--p4-password", "-p4P", dest="password", help="P4 password", metavar="P4PASSWD")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.check_required_option("port", """
            The perforce 'port' is not specified.

            The perforce port defines protocol, host and listening port of the perforce
            server. Please specify perforce port by using '--p4-port' ('-p4p') command line
            parameter or by setting P4PORT environment variable.
            """)
        self.check_required_option("user", """
            The perforce user name is not specified.

            The perforce user name is required to authenticate with perforce server. Please
            specify the perforce user name by using '--p4-user' ('-p4u') command line
            parameter or by setting P4USER environment variable.
            """)
        self.check_required_option("password", """
            The perforce password is not specified.

            The perforce password is required to authenticate with perforce server. Please
            specify the perforce password by using '--p4-password' ('-p4P') command line
            parameter or by setting P4PASSWD environment variable.
            """)

        try:
            p4_module = cast(P4stub, importlib.import_module("P4"))
        except ImportError as e:
            text = "Error: using VCS type 'p4' requires official Helix CLI and Python package 'perforce-p4python' " \
                   "to be installed. Please refer to `Prerequisites` chapter of project documentation for " \
                   "detailed instructions"
            raise ImportError(text) from e

        # By putting P4 object to self, we can use it in this or any derived classes without any further imports
        self.p4 = p4_module.P4()
        global P4Exception
        P4Exception = p4_module.P4Exception

    @make_block("Connecting")
    @catch_p4exception()
    def connect(self):
        self.disconnect()
        self.p4.port = self.settings.port
        self.p4.user = self.settings.user
        self.p4.password = self.settings.password

        self.p4.connect()
        self.append_repo_status("Perforce server: " + self.settings.port + "\n\n")

    @make_block("Disconnecting")
    def disconnect(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            self.p4.disconnect()
            if not w:
                return
            if "Not connected" in str(w[0].message):  # We consider it ok for a session to expire or not be created yet
                return
            text = ""
            for line in w:
                text += "\n" + warnings.formatwarning(str(line.message), line.category, line.filename, line.lineno)
            self.structure.fail_current_block("Unexpected warning(s): " + text)
            raise SilentAbortException()

    def finalize(self):
        with Uninterruptible(self.out.log_exception) as run:
            run(self.disconnect)
            run(super().finalize)


class PerforceSubmitVcs(PerforceVcs, base_vcs.BaseSubmitVcs):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Perforce")
        parser.add_argument("--p4-client", "-p4c", dest="client", metavar="P4CLIENT",
                            help="Existing P4 client (workspace) name to use for submitting")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.check_required_option("client", """
            Perforce workspace name is not specified.
            
            This parameter is required for submitting changes to the perforce. It defines
            the name of the existing workspace to use for submit. Please specify the
            workspace name by using '--p4-client' ('-p4c') command-line parameter or
            P4CLIENT environment variable.
            """)

    def p4reconcile(self, *args, **kwargs):
        try:
            return self.p4.run_reconcile(*args, **kwargs)
        except P4Exception as e:
            if not e.warnings:
                raise P4Exception from e
            if "no file(s) to reconcile" not in e.warnings[0]:
                raise P4Exception from e
            return []

    def reconcile_one_path(self, file_path, workspace_root, change_id, edit_only):
        # TODO: cover 'not file_path.startswith("/")' case with tests
        if not file_path.startswith("/"):
            file_path = workspace_root + "/" + file_path
        if file_path.endswith("/"):
            file_path += "..."
        if edit_only:
            reconcile_result = self.p4reconcile("-c", change_id, "-e", convert_to_str(file_path))
            if not reconcile_result:
                self.out.log(
                    "The file was not edited. Skipping '{}'...".format(os.path.relpath(file_path, workspace_root)))
        else:
            reconcile_result = self.p4reconcile("-c", change_id, convert_to_str(file_path))

        for line in reconcile_result:
            # p4reconcile returns list of dicts AND strings if file is opened in another workspace
            # so we catch TypeError if line is not dict
            try:
                if line["action"] == "add":
                    self.p4.run_reopen("-c", change_id, "-t", "+w", line["depotFile"])
            except TypeError:
                self.out.log(line)

    @catch_p4exception()
    def submit_new_change(self, description, file_list, review=False, edit_only=False):
        self.connect()

        if review:
            raise CriticalCiException("'--create-review' option is not supported for Perforce at the moment")

        if not self.p4.run_clients("-e", self.settings.client):
            raise CriticalCiException("Workspace '" + self.settings.client + "' doesn't exist!")
        self.p4.client = self.settings.client
        client = self.p4.fetch_client(self.settings.client)
        workspace_root = client['Root']

        change = self.p4.fetch_change()
        change["Files"] = []
        change["Description"] = description
        change_id = self.p4.save_change(change)[0].split()[1]

        try:
            for file_path in file_list:
                self.reconcile_one_path(file_path, workspace_root, change_id, edit_only)

            current_cl = self.p4.fetch_change(change_id)
            # If no changes were reconciled, there will be no file records in CL dictionary
            if "Files" not in current_cl:
                self.p4.run_change("-d", change_id)
                return 0

            self.p4.run_submit(current_cl, "-f", "revertunchanged")
        except Exception as e:
            self.p4.run_revert("-k", "-c", change_id, "//...")
            self.p4.run_change("-d", change_id)
            raise CriticalCiException(str(e)) from e

        return change_id


class PerforceWithMappings(PerforceVcs):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Perforce")

        parser.add_argument("--p4-project-depot-path", "-p4d", dest="project_depot_path", metavar="P4_PATH",
                            help="Depot path to get sources from (starts with '//', ends with '/...'"
                                 "Only supports one path. Cannot be used with '--p4-mappings' option")

        parser.add_argument("--p4-mappings", "-p4m", dest="mappings", action="append", nargs='+',
                            metavar="P4_MAPPINGS",
                            help="P4 mappings. Cannot be used with '--p4-project-depot-path' option. "
                                 "Use the following format: '//depot/path/... /local/path/...', "
                                 "where the right half is the same as in real P4 mappings, "
                                 "but without client name. Just start from client root with one slash. "
                                 "For more than one add several times or split with ',' character")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not getattr(self.settings, "project_depot_path", None) and not getattr(self.settings, "mappings", None):
            self.error("""
                Both P4_PATH (-p4d) and P4_MAPPINGS (-p4m) are not set.
                
                Universum needs one of these parameters to be set in order to download sources.
                """)

        # Convert old-style depot path into mappings
        if self.settings.project_depot_path:
            if self.settings.mappings:
                self.error("Both 'P4_PATH' and 'P4_MAPPINGS' cannot be processed simultaneously")
            mappings = [self.settings.project_depot_path + " /..."]
        else:
            mappings = self.settings.mappings

        self.mappings = utils.unify_argument_list(mappings)


class PerforceMainVcs(PerforceWithMappings, base_vcs.BaseDownloadVcs):
    swarm_factory = Dependency(Swarm)
    artifacts_factory = Dependency(ArtifactCollector)
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Perforce")

        parser.add_argument("--p4-client", "-p4c", dest="client", metavar="P4CLIENT",
                            help="P4 client (workspace) name to be created. "
                                 "Use '--p4-force-clean' option to delete this client while finalizing")

        parser.add_argument("--p4-sync", "-p4h", action="append", nargs='+', dest="sync_cls",
                            metavar="SYNC_CHANGELIST",
                            help="Sync (head) CL(s). Just a number will be interpreted as united CL for "
                                 "all added VCS roots. To add a sync CL for specific depot/workspace location, "
                                 "write location in the same format as in P4_MAPPINGS with '@<CL number>' "
                                 "in the end, e.g. '//DEV/Solution/MyProject/...@1234567'. To specify "
                                 "more than one sync CL for several locations, add '--p4-sync' several times "
                                 "or split them with comma")

        parser.add_argument("--p4-shelve", "-p4s", action="append", nargs='+', dest="shelve_cls",
                            metavar="SHELVE_CHANGELIST",
                            help="List of shelve CLs to be applied, separated by comma. "
                                 "--p4-shelve can be added to the command line several times. "
                                 "Also shelve CLs can be specified via additional environment variables: "
                                 "SHELVE_CHANGELIST_1..5")

        parser.add_argument("--p4-force-clean", action="store_true", dest="force_clean",
                            help="**Revert all vcs within '--p4-client' and delete the workspace.** "
                                 "Mandatory for CI environment, otherwise use with caution")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.check_required_option("client", """
            Perforce workspace name is not specified.
        
            This parameter is required for creating temporary workspace for downloading
            project sources. Please specify the workspace name by using '--p4-client'
            ('-p4c') command-line parameter or P4CLIENT environment variable.
            """)

        self.artifacts = self.artifacts_factory()
        self.reporter = self.reporter_factory()
        # self.swarm is initialized by self.code_review()
        self.swarm = None

        self.client_name = self.settings.client
        self.client_root = self.settings.project_root

        self.sync_cls = []
        self.shelve_cls = []
        self.depots = []
        self.client_view = []
        self.mappings_dict = {}

        self.unshelved_files: List[Dict[str, str]] = []
        self.diff_in_files: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []

    def code_review(self):
        self.swarm = self.swarm_factory(self.settings.user, self.settings.password)
        return self.swarm

    def get_related_cls(self, cl_number):
        cl_list = [cl_number]
        description = self.p4.run_describe(cl_number)[0]
        for entry in description['desc'].splitlines():
            if entry.startswith("[Related change IDs]"):
                cl_list.extend([number.strip() for number in entry.strip("[Related change IDs]").split(",")])

        return cl_list

    def expand_workspace_parameters(self):
        # Create a list of depots for sync
        for mapping in self.mappings:
            splat_mapping = mapping.split(" ")
            self.depots.append({"path": splat_mapping[0]})
            self.client_view.append(splat_mapping[0] + " //" + self.client_name + splat_mapping[-1])

        # Finalize the list of depots for sync: merge and define sync CLs
        self.sync_cls = utils.unify_argument_list(self.settings.sync_cls)
        if len(self.sync_cls) == 1 and self.sync_cls[0].isdigit():
            for depot in self.depots:
                depot["cl"] = self.sync_cls[0]

        else:
            for depot in self.depots:
                depot["cl"] = None

            for entry in self.sync_cls:
                splat_entry = entry.split("@")
                # Remove identical depot entries, mostly for aesthetic reasons
                for index, depot in enumerate(self.depots):
                    if splat_entry[0] == depot["path"]:
                        self.depots.pop(index)
                self.depots.append({"path": splat_entry[0], "cl": splat_entry[1]})

        # Retrieve list of shelved CLs from Swarm and "classic" environment variables
        cls = []
        if self.swarm:
            swarm_cls = self.get_related_cls(self.swarm.settings.change)
            cls.extend(swarm_cls)
        for x in range(1, 6):
            cls.append(os.getenv("SHELVE_CHANGELIST_" + str(x)))
        self.shelve_cls = sorted(list(set(utils.unify_argument_list(self.settings.shelve_cls, additional_list=cls))))

    def p4report(self, report):
        for line in report:
            if isinstance(line, dict):
                self.out.log(line["depotFile"] + " (" + line["action"] + ")")

    @make_block("Creating workspace")
    @catch_p4exception()
    def create_workspace(self):
        self.expand_workspace_parameters()

        if not all((self.client_name, self.client_root, self.client_view)):
            raise CriticalCiException("Workspace is not created. Some of these parameters are missing: "
                                      "client name, root directory or mappings.")

        if self.settings.force_clean:
            self.clean_workspace()

        if self.p4.run_clients("-e", self.client_name):
            raise CriticalCiException("Workspace '" + self.client_name + "' already exists!")

        client = self.p4.fetch_client(self.client_name)
        client["Root"] = convert_to_str(self.client_root)
        client["View"] = self.client_view
        self.p4.save_client(client)
        self.p4.client = self.client_name
        self.out.log("Workspace '" + self.client_name + "' created/updated.")

        self.append_repo_status("Workspace: " + self.client_name + "\n")
        self.append_repo_status("Workspace root: " + self.client_root + "\n")
        self.append_repo_status("Mappings:\n")
        for line in self.client_view:
            self.append_repo_status("    " + line + "\n")

    @make_block("Downloading")
    @catch_p4exception()
    def sync(self):
        self.sources_need_cleaning = True        # pylint: disable=attribute-defined-outside-init
        self.append_repo_status("Sync CLs:\n")

        for idx, depot in enumerate(self.depots):
            if depot["cl"] is None:
                self.out.log("Getting latest CL number for '" + depot["path"] + "'")
                try:
                    depot["cl"] = self.p4.run_changes("-m", "1", "-s", "submitted", depot["path"])[0]["change"]
                except IndexError as e:
                    text = "Error getting latest CL number for '" + depot["path"] + "'"
                    text += "\nPlease check depot path formatting (e.g. '/...' in the end for directories)"
                    raise CriticalCiException(text) from e
                self.out.log("Latest CL: " + depot["cl"])

            line = depot["path"] + '@' + depot["cl"]
            # Set environment variable for each mapping in order of there definition
            os.environ["SYNC_CL_{}".format(idx)] = depot["cl"]

            self.out.log("Downloading " + line)
            try:
                result = self.p4.run_sync("-f", line)
            except P4Exception as e:
                if "not in client view" not in str(e):
                    raise CriticalCiException(str(e)) from e

                text = f"{e}\nPossible reasons of this error:"
                text += "\n * Wrong formatting (e.g. no '/...' in the end of directory path)"
                text += "\n * Location in 'SYNC_CHANGELIST' is not actually located inside any of 'P4_MAPPINGS'"
                raise CriticalCiException(text) from e

            self.append_repo_status(f"    {line}\n")
            self.out.log(f"Downloaded {result[0]['totalFileCount']} files.")

    def p4unshelve(self, *args, **kwargs):
        try:
            result = self.p4.run_unshelve(*args, **kwargs)
        except P4Exception as e:
            if "already committed" in str(e) and self.swarm and len(self.shelve_cls) == 1:
                self.out.log("CL already committed")
                self.out.report_build_status("CL already committed")
                self.swarm = None
                raise SilentAbortException(application_exit_code=0) from e
            raise P4Exception from e
        return result

    @make_block("Unshelving")
    @catch_p4exception()
    def unshelve(self):
        if self.shelve_cls:
            self.append_repo_status("Shelve CLs:")
            for cl in self.shelve_cls:
                self.out.log("Unshelve CL " + cl)
                report = self.p4unshelve("-s", cl, "-f")
                self.map_local_path_to_depot(report)
                self.p4report(report)
                self.append_repo_status(" " + cl)
            self.append_repo_status("\n")

    @catch_p4exception(ignore_if="file(s) up-to-date")
    def check_diff_for_depot(self, depot: str) -> str:
        try:
            p4cmd = sh.Command("p4")
            diff_result = p4cmd("-c", self.settings.client, "-u", self.settings.user,
                                "-P", self.settings.password, "-p", self.settings.port,
                                "diff", depot)
            result: str = utils.trim_and_convert_to_unicode(diff_result.stdout)
        except sh.ErrorReturnCode as e:
            for line in e.stderr.splitlines():
                if not (line.startswith("Librarian checkout")
                        or line.startswith("Error opening librarian file")
                        or line.startswith("Transfer of librarian file")
                        or line.endswith(".gz: No such file or directory")):
                    raise CriticalCiException(utils.trim_and_convert_to_unicode(e.stderr)) from e
            result = utils.trim_and_convert_to_unicode(e.stdout)
        return result

    def calculate_file_diff(self) -> List[Dict[str, str]]:
        action_list: Dict[str, str] = {}
        for entry in self.p4.run_opened():
            action_list[entry["depotFile"]] = entry["action"]
        if not action_list:
            return [{}]

        result: List[Dict[str, str]] = []
        # Both 'p4 opened' and 'p4 where' entries have same key 'depotFile'
        for entry in self.p4.run_where(list(action_list.keys())):
            result.append({"action": action_list[entry["depotFile"]],
                           "repo_path": entry["depotFile"],
                           "local_path": entry["path"]})
        return result

    @make_block("Checking diff")
    def diff(self) -> None:
        rep_diff: List[str] = []
        for depot in self.depots:
            line: str = depot["path"] + '@' + depot["cl"]
            result: str = self.check_diff_for_depot(line)
            if result:
                rep_diff.append(result + "\n")

        if rep_diff:
            file_name = "REPOSITORY_DIFFERENCE.txt"
            self.append_repo_status("See '" + file_name + "' for details on unshelved changes\n")

            f: TextIO = self.artifacts.create_text_file(file_name)
            for result in rep_diff:
                f.write(result)
            f.close()

    def map_local_path_to_depot(self, report):
        for line in report:
            if isinstance(line, dict):
                abs_path = self.p4.run("where", line["depotFile"])[0]["path"]
                self.mappings_dict[abs_path] = line["depotFile"]

    @make_block("Revert workspace to depot state")
    @catch_p4exception()
    def copy_cl_files_and_revert(self) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
        self.unshelved_files = self.p4.run_opened()
        unshelved_path: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []

        unshelved_filtered: List[Dict[str, str]] =\
            [item for item in self.unshelved_files if item["action"] != "move/delete"]

        for item in unshelved_filtered:
            relative: Optional[str] = None
            copied: Optional[str] = None
            absolute: Optional[str]
            if item["action"] == "delete":
                absolute = os.path.join(self.client_root, item["clientFile"].replace("//" + item["client"] + "/", ""))
            else:
                relative = item["clientFile"].replace("//" + item["client"] + "/", "")
                copied = os.path.join(self.client_root, "new_temp", relative)
                absolute = os.path.join(self.client_root, relative)
                try:
                    shutil.copy(absolute, copied)
                except IOError:
                    os.makedirs(os.path.dirname(copied))
                    shutil.copy(absolute, copied)
                # absolute = None to make sure content of 'add' and 'branch' won't participate in diff after revert
                # for 'branch' diff we will assume it is a new file
                # be careful, file for 'add' will be present in repo after revert
                if item["action"] in ["add", "branch"]:
                    absolute = None
            unshelved_path.append((relative, copied, absolute))

        if self.shelve_cls:
            self.p4.run_revert("//...")

            for item, path in zip(unshelved_filtered, unshelved_path):
                relative, copied, absolute = path
                if item["action"] == "move/add":
                    for local, depot in self.mappings_dict.items():
                        if depot == item["movedFile"]:
                            absolute = local
                self.diff_in_files.append((relative, copied, absolute))
        return self.diff_in_files

    def prepare_repository(self):
        self.connect()
        self.create_workspace()
        self.sync()
        self.unshelve()
        self.diff()
        if self.swarm:
            self.swarm.client_root = self.client_root
            self.swarm.mappings_dict = self.mappings_dict

    @make_block("Cleaning workspace", pass_errors=False)
    def clean_workspace(self):
        try:
            self.p4.client = self.client_name
            report = self.p4.run_revert("-k", "-c", "default", "//...")
            self.p4report(report)
            shelves = self.p4.run_changes("-c", self.client_name, "-s", "shelved")
            for item in shelves:
                self.out.log("Deleting shelve from CL " + item["change"])
                self.p4.run_shelve("-d", "-c", item["change"])
            all_cls = self.p4.run_changes("-c", self.client_name, "-s", "pending")
            for item in all_cls:
                self.out.log("Deleting CL " + item["change"])
                self.p4.run_revert("-k", "-c", item["change"], "//...")
                self.p4.run_change("-d", item["change"])
        except P4Exception as e:
            if "Client '{}' unknown".format(self.client_name) not in e.value \
                    and "file(s) not opened on this client" not in e.value:
                self.structure.fail_current_block(e.value)
        try:
            self.p4.delete_client(self.client_name)
        except P4Exception as e:
            if "Client '{}' doesn't exist".format(self.client_name) not in e.value:
                self.structure.fail_current_block(e.value)

    def finalize(self):
        with Uninterruptible(self.out.log_exception) as run:
            if self.settings.force_clean:
                run(self.connect)
                run(self.clean_workspace)
            run(self.disconnect)
            run(super().finalize)


class PerforcePollVcs(PerforceWithMappings, base_vcs.BasePollVcs):
    def get_changes(self, changes_reference=None, max_number='1'):
        self.connect()

        if not changes_reference:
            changes_reference = {}
        result = {}

        for depot in self.mappings:
            depot_path = depot.split(" ")[0]
            if depot_path not in result:
                result[depot_path] = []

            changes = self.p4.run_changes("-s", "submitted", "-m1", depot_path)
            last_cl = changes[0]["change"]
            reference_cl = changes_reference.get(depot_path, last_cl)

            rev_range_string = depot_path + "@" + reference_cl + ",#head"
            submitted_cls = self.p4.run_changes("-s", "submitted", "-m" + str(max_number), rev_range_string)

            submitted_cls.reverse()
            for cl in submitted_cls:
                result[depot_path].append(cl["change"])

        return result
