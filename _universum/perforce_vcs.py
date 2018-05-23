# -*- coding: UTF-8 -*-

import os
import warnings

import sh
from P4 import P4, P4Exception

from . import base_classes, swarm, utils, artifact_collector
from .ci_exception import CriticalCiException, SilentAbortException
from .gravity import Dependency
from .module_arguments import IncorrectParameterError
from .output import needs_output
from .structure_handler import needs_structure
from .utils import Uninterruptible, make_block

__all__ = [
    "PerforceVcs",
    "catch_p4exception"
]


def catch_p4exception(ignore_if=None):
    return utils.catch_exception(P4Exception, ignore_if)


@needs_output
@needs_structure
class PerforceVcs(base_classes.VcsBase):
    swarm_factory = Dependency(swarm.Swarm)
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)

    """
    This class contains CI functions for interaction with Perforce
    """

    # TODO: split into several classes to remove hide_sync_options, which doesn't work anyway
    @staticmethod
    def define_arguments(argument_parser, hide_sync_options=False):
        parser = argument_parser.get_or_create_group("Perforce",
                                                     "Please read the details about P4 environment variables "
                                                     "in official Helix manual")

        parser.add_hidden_argument("--p4-sync", "-p4h", action="append", nargs='+', dest="sync_cls",
                                   is_hidden=hide_sync_options, metavar="SYNC_CHANGELIST",
                                   help="Sync (head) CL(s). Just a number will be interpreted as united CL for "
                                        "all added VCS roots. To add a sync CL for specific depot/workspace location, "
                                        "write location in the same format as in P4_MAPPINGS with '@<CL number>' "
                                        "in the end, e.g. '//DEV/Solution/MyProject/...@1234567'. To specify "
                                        "more than one sync CL for several locations, add '--p4-sync' several times "
                                        "or split them with comma")

        parser.add_hidden_argument("--p4-shelve", "-p4s", action="append", nargs='+', dest="shelve_cls",
                                   is_hidden=hide_sync_options, metavar="SHELVE_CHANGELIST",
                                   help="List of shelve CLs to be applied, separated by comma. "
                                        "--p4-shelve can be added to the command line several times. "
                                        "Also, 5 additional shelve CLs can be specified via environment variables: "
                                        "SHELVE_CHANGELIST_1..5.")

        parser.add_argument("--p4-port", "-p4p", dest="port", help="P4 port (e.g. 'myhost.net:1666')",
                            metavar="P4PORT")
        parser.add_argument("--p4-user", "-p4u", dest="user", help="P4 user name", metavar="P4USER")
        parser.add_argument("--p4-password", "-p4P", dest="password", help="P4 password", metavar="P4PASSWD")

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

        parser.add_hidden_argument("--p4-client", "-p4c", dest="client", metavar="P4CLIENT",
                                   is_hidden=hide_sync_options,
                                   help="P4 client (workspace) name. "
                                        "Use '--p4-force-clean' option to make a disposable client")
        parser.add_hidden_argument("--p4-force-clean", action="store_true", dest="force_clean",
                                   is_hidden=hide_sync_options,
                                   help="**Revert all files within '--p4-client' and delete the workspace.** "
                                        "Mandatory for CI environment, otherwise use with caution")

    def check_required_option(self, name, env_var):
        if getattr(self.settings, name) is None:
            raise IncorrectParameterError(env_var + " is not specified. Communication with perforce server "
                                          "requires setting P4PORT, P4USER and P4PASSWD")

    def __init__(self, settings, project_root, report_to_review):
        super(PerforceVcs, self).__init__(settings, project_root)
        self.report_to_review = report_to_review
        self.artifacts = None
        self.swarm = None

        self.p4 = P4()

        self.check_required_option("port", "P4PORT")
        self.check_required_option("user", "P4USER")
        self.check_required_option("password", "P4PASSWD")

        self.client_name = None
        self.client_root = None
        self.sync_cls = []
        self.shelve_cls = []
        self.depots = []
        self.client_view = []

        self.mappings_dict = {}

        # Convert old-style depot path into mappings
        if self.settings.project_depot_path:
            if self.settings.mappings:
                raise IncorrectParameterError("Both 'P4_PATH' and 'P4_MAPPINGS' cannot be processed simultaneously")
            self.mappings = [self.settings.project_depot_path + " /..."]
        else:
            self.mappings = self.settings.mappings

        self.mappings = utils.unify_argument_list(self.mappings)

        if self.report_to_review:
            self.swarm = self.swarm_factory(self.settings.user, self.settings.password)

    @make_block("Connecting")
    @catch_p4exception()
    def connect(self):
        self.p4.port = self.settings.port
        self.p4.user = self.settings.user
        self.p4.password = self.settings.password

        self.p4.connect()
        self.append_repo_status("Perforce server: " + self.settings.port + "\n\n")

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
            submitted_cls = self.p4.run_changes("-s", "submitted", "-m" + unicode(max_number), rev_range_string)

            submitted_cls.reverse()
            for cl in submitted_cls:
                result[depot_path].append(cl["change"])

        return result

    def p4reconcile(self, *args, **kwargs):
        try:
            return self.p4.run_reconcile(*args, **kwargs)
        except P4Exception as e:
            if not e.warnings:
                raise
            if "no file(s) to reconcile" not in e.warnings[0]:
                raise
            return []

    def submit_new_change(self, description, file_list, review=False, edit_only=False):
        self.connect()

        if review:
            raise CriticalCiException("'--create-review' option is not supported for Perforce at the moment")

        if not self.p4.run_clients("-e", self.settings.client):
            raise CriticalCiException("Workspace '" + self.settings.client + "' doesn't exist!")
        self.p4.client = self.settings.client
        client = self.p4.fetch_client(self.settings.client)
        workspace_root = client['Root']

        for file_path in file_list:
            # TODO: cover 'not file_path.startswith("/")' case with tests
            if not file_path.startswith("/"):
                file_path = workspace_root + "/" + file_path
            if file_path.endswith("/"):
                file_path += "..."
            if edit_only:
                reconcile_result = self.p4reconcile("-e", file_path)
                if not reconcile_result:
                    self.out.log("The file was not edited. Skipping '{}'...".format(os.path.relpath(file_path, workspace_root)))
            else:
                reconcile_result = self.p4reconcile(file_path)

            for line in reconcile_result:
                if line["action"] == "add":
                    self.p4.run_reopen("-t", "+w", line["depotFile"])

        current_cl = self.p4.fetch_change()
        current_cl['Description'] = description

        # If no changes were reconciled, there will be no file records in CL dictionary
        if "Files" not in current_cl:
            return 0

        result = self.p4.run_submit(current_cl, "-f", "revertunchanged")
        cl_number = result[-1]['submittedChange']

        return cl_number

    def expand_workspace_parameters(self):
        # Prepare workspace settings: client root & view; create a list of depots for sync
        self.client_name = self.settings.client
        self.client_root = self.project_root
        for mapping in self.mappings:
            splat_mapping = mapping.split(" ")
            self.depots.append({"path": splat_mapping[0]})
            self.client_view.append(splat_mapping[0] + " //" + self.client_name + splat_mapping[1])

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

        # Retrieve list of shelved CLs from "classic" environment variables
        cls = []
        for x in range(1, 6):
            cls.append(os.getenv("SHELVE_CHANGELIST_" + unicode(x)))
        self.shelve_cls = sorted(list(set(utils.unify_argument_list(self.settings.shelve_cls, additional_list=cls))))

    def p4report(self, report):
        for line in report:
            if isinstance(line, dict):
                self.out.log(line["depotFile"] + " (" + line["action"] + ")")

    @make_block("Cleaning workspace", pass_errors=False)
    @catch_p4exception(ignore_if="doesn't exist")
    def clean_workspace(self):
        try:
            self.p4.client = self.client_name
            report = self.p4.run_revert("//...")
            self.p4report(report)
        except P4Exception:
            pass
        self.p4.delete_client(self.client_name)

    @make_block("Creating workspace")
    @catch_p4exception()
    def create_workspace(self):
        if not getattr(self.settings, "client"):
            raise CriticalCiException("P4CLIENT is not specified. Cannot create workspace")

        self.expand_workspace_parameters()

        if not all((self.client_name, self.client_root, self.client_view)):
            raise CriticalCiException("Workspace is not created. Some of these parameters are missing: "
                                      "client name, root directory or mappings.")

        if self.settings.force_clean:
            self.clean_workspace()

        if self.p4.run_clients("-e", self.client_name):
            raise CriticalCiException("Workspace '" + self.client_name + "' already exists!")

        client = self.p4.fetch_client(self.client_name)
        client["Root"] = self.client_root
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
        self.sources_need_cleaning = True
        self.append_repo_status("Sync CLs:\n")

        for idx, depot in enumerate(self.depots):
            if depot["cl"] is None:
                self.out.log("Getting latest CL number for '" + depot["path"] + "'")
                try:
                    depot["cl"] = self.p4.run_changes("-m", "1", "-s", "submitted", depot["path"])[0]["change"]
                except IndexError:
                    text = "Error getting latest CL number for '" + depot["path"] + "'"
                    text += "\nPlease check depot path formatting (e.g. '/...' in the end for directories)"
                self.out.log("Latest CL: " + depot["cl"])

            line = depot["path"] + '@' + depot["cl"]
            # Set environment variable for each mapping in order of there definition
            os.environ["SYNC_CL_{}".format(idx)] = depot["cl"]

            self.out.log("Downloading " + line)
            try:
                result = self.p4.run_sync("-f", line)
            except P4Exception as e:
                if "not in client view" in unicode(e):
                    text = unicode(e) + "Possible reasons of this error:"
                    text += "\n * Wrong formatting (e.g. no '/...' in the end of directory path)"
                    text += "\n * Location in 'SYNC_CHANGELIST' is not actually located inside any of 'P4_MAPPINGS'"
                    raise CriticalCiException(text)
                else:
                    raise CriticalCiException(unicode(e))

            self.append_repo_status("    " + line + "\n")
            self.out.log("Downloaded {} files.".format(result[0]["totalFileCount"]))

    def p4unshelve(self, *args, **kwargs):
        try:
            result = self.p4.run_unshelve(*args, **kwargs)
        except P4Exception as e:
            if "already committed" in unicode(e) and self.report_to_review and len(self.shelve_cls) == 1:
                self.out.log("CL already committed")
                self.out.report_build_status("CL already committed")
                self.swarm = None
                raise SilentAbortException(application_exit_code=0)
            raise
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
    def check_diff_for_depot(self, depot):
        try:
            p4cmd = sh.Command("p4")
            result = utils.trim_and_convert_to_unicode(p4cmd("-c", self.settings.client, "-u", self.settings.user,
                                                             "-P", self.settings.password, "-p", self.settings.port,
                                                             "diff", depot))
        except sh.ErrorReturnCode as e:
            for line in e.stderr.splitlines():
                if not (line.startswith("Librarian checkout")
                        or line.startswith("Error opening librarian file")
                        or line.startswith("Transfer of librarian file")
                        or line.endswith(".gz: No such file or directory")):
                    raise CriticalCiException(utils.trim_and_convert_to_unicode(e.stderr))
            result = utils.trim_and_convert_to_unicode(e.stdout)
        return result

    @make_block("Checking diff")
    def diff(self):
        self.artifacts = self.artifacts_factory()
        rep_diff = []
        for depot in self.depots:
            line = depot["path"] + '@' + depot["cl"]
            result = self.check_diff_for_depot(line)
            if result:
                rep_diff.append(result + "\n")

        if rep_diff:
            file_name = "REPOSITORY_DIFFERENCE.txt"
            self.append_repo_status("See '" + file_name + "' for details on unshelved changes\n")

            f = self.artifacts.create_text_file(file_name)
            for result in rep_diff:
                f.write(result)
            f.close()

    @make_block("Disconnecting")
    def disconnect(self):
        with warnings.catch_warnings(record=True) as w:
            self.p4.disconnect()
            if not w:
                return
            if "Not connected" in w[0].message.message:
                text = "Perforce client is not connected on disconnect. Something must have gone wrong"
                self.structure.fail_current_block(text)
            else:
                text = ""
                for line in w:
                    text += "\n" + warnings.formatwarning(line.message, line.category, line.filename, line.lineno)
                self.structure.fail_current_block("Unexpected warning(s): " + text)
            raise SilentAbortException()

    def map_local_path_to_depot(self, report):
        for line in report:
            if isinstance(line, dict):
                abs_path = self.p4.run("where", line["depotFile"])[0]["path"]
                self.mappings_dict[abs_path] = line["depotFile"]

    def prepare_repository(self):
        self.connect()
        self.create_workspace()
        self.sync()
        self.unshelve()
        self.diff()
        if self.report_to_review:
            self.swarm.client_root = self.client_root
            self.swarm.mappings_dict = self.mappings_dict

    def finalize(self):
        with Uninterruptible() as run:
            if self.settings.force_clean:
                run(self.clean_workspace)
            run(self.disconnect)
            run(super(PerforceVcs, self).finalize)
