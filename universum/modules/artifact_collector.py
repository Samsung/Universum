from typing import List, Dict

import codecs
import distutils
from distutils import dir_util, errors
import os
import shutil
import zipfile

import glob2

from ..lib.ci_exception import CriticalCiException, CiException
from ..lib.gravity import Dependency
from ..lib.utils import make_block
from ..lib import utils
from .automation_server import AutomationServerForHostingBuild
from .output import HasOutput
from .project_directory import ProjectDirectory
from .reporter import Reporter
from .structure_handler import HasStructure

__all__ = [
    "ArtifactCollector"
]


def make_big_archive(target, source):
    save_cwd = os.getcwd()
    if source is not None:
        target = os.path.abspath(target)
        os.chdir(source)
    base_dir = os.curdir

    try:
        filename = target + ".zip"
        archive_dir = os.path.dirname(target)

        if archive_dir and not os.path.exists(archive_dir):
            os.makedirs(archive_dir)

        with zipfile.ZipFile(filename, "w", compression=zipfile.ZIP_DEFLATED,
                             allowZip64=True) as zf:
            path = os.path.normpath(base_dir)
            zf.write(path, path)
            for dirpath, dirnames, filenames in os.walk(base_dir):
                for name in sorted(dirnames):
                    path = os.path.normpath(os.path.join(dirpath, name))
                    zf.write(path, path)
                for name in filenames:
                    path = os.path.normpath(os.path.join(dirpath, name))
                    if os.path.isfile(path):
                        zf.write(path, path)
    finally:
        if source is not None:
            os.chdir(save_cwd)

    return filename


class ArtifactCollector(ProjectDirectory, HasOutput, HasStructure):
    reporter_factory = Dependency(Reporter)
    automation_server_factory = Dependency(AutomationServerForHostingBuild)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Artifact collection",
                                                     "Parameters of archiving and collecting of build artifacts")

        parser.add_argument("--artifact-dir", "-ad", dest="artifact_dir", metavar="ARTIFACT_DIR",
                            help="Directory to collect artifacts to. Default is 'artifacts'")

        parser.add_argument("--no-archive", action="store_true", dest="no_archive",
                            help="By default all directories noted as artifacts are copied as .zip archives. "
                                 "This option turn archiving off to copy bare directories to artifact directory")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reporter = self.reporter_factory()
        self.automation_server = self.automation_server_factory()

        self.artifact_list = []
        self.report_artifact_list = []

        # Needed because of wildcards
        self.collected_report_artifacts = set()

        self.file_list = set()
        self.artifact_dir = self.settings.artifact_dir

        if not self.artifact_dir:
            self.artifact_dir = os.path.join(os.getcwd(), "artifacts")
        if not os.path.exists(self.artifact_dir):
            os.makedirs(self.artifact_dir)

    def make_file_name(self, name):
        return utils.calculate_file_absolute_path(self.artifact_dir, name)

    def create_text_file(self, name):
        try:
            file_name = self.make_file_name(name)
            if file_name not in self.file_list:
                if os.path.exists(file_name):
                    text = "File '" + os.path.basename(file_name) + "' already exists in artifact directory." + \
                           "\nPossible reason of this error: previous build artifacts are not cleaned"
                    raise CriticalCiException(text)

            self.file_list.add(file_name)
            file_path = self.automation_server.artifact_path(self.artifact_dir, os.path.basename(file_name))
            self.out.log("Adding file " + file_path + " to artifacts...")
            return codecs.open(file_name, "a", encoding="utf-8")

        except IOError as e:
            raise CiException("The following error occurred while working with file: " + str(e)) from e

    def preprocess_artifact_list(self, artifact_list, ignore_already_existing=False):
        """
        Check artifacts for existence; remove if required; raise exception otherwise; sort and remove duplicates
        :param artifact_list: list of dictionaries with keys 'path' (for path) and 'clean' to clean it before build
        :param ignore_already_existing: will not check existence of artifacts when set to 'True'
        :return: sorted list of checked paths (including duplicates and wildcards)
        """
        dir_list = set()
        for item in artifact_list:
            # Check existence in place: wildcards applied
            matches = glob2.glob(item["path"])
            if matches:
                if item["clean"]:
                    for matching_path in matches:
                        try:
                            os.remove(matching_path)  # TODO: use shutil by default
                        except OSError as e:
                            if "Is a directory" not in e.strerror:
                                raise
                            shutil.rmtree(matching_path)
                elif not ignore_already_existing:
                    text = "Build artifacts, such as"
                    for matching_path in matches:
                        text += "\n * '" + os.path.basename(matching_path) + "'"
                    text += "\nalready exist in '" + os.path.dirname(item["path"]) + "' directory."
                    text += "\nPossible reason of this error: previous build results in working directory"
                    raise CriticalCiException(text)

            # Check existence in 'artifacts' directory: wildcards NOT applied
            path_to_check1 = os.path.join(self.artifact_dir, os.path.basename(item["path"]))
            path_to_check2 = os.path.join(path_to_check1 + ".zip")
            if os.path.exists(path_to_check1) or os.path.exists(path_to_check2):
                text = "Build artifact '" + os.path.basename(item["path"]) + "' already present in artifact directory."
                text += "\nPossible reason of this error: previous build results in working directory"
                raise CriticalCiException(text)

            dir_list.add(item["path"])
        new_artifact_list = list(dir_list)
        new_artifact_list.sort(key=len, reverse=True)
        return new_artifact_list

    @make_block("Preprocessing artifact lists")
    def set_and_clean_artifacts(self, project_configs, ignore_existing_artifacts=False):
        artifact_list = []
        report_artifact_list = []
        for configuration in project_configs.all():
            if "artifacts" in configuration:
                path = utils.parse_path(configuration["artifacts"], self.settings.project_root)
                clean = configuration.get("artifact_prebuild_clean", False)
                artifact_list.append(dict(path=path, clean=clean))
            if "report_artifacts" in configuration:
                path = utils.parse_path(configuration["report_artifacts"], self.settings.project_root)
                clean = configuration.get("artifact_prebuild_clean", False)
                report_artifact_list.append(dict(path=path, clean=clean))

        if artifact_list:
            name = "Setting and preprocessing artifacts according to configs"
            self.artifact_list = self.structure.run_in_block(self.preprocess_artifact_list,
                                                             name, True, artifact_list, ignore_existing_artifacts)
        if report_artifact_list:
            name = "Setting and preprocessing artifacts to be mentioned in report"
            self.report_artifact_list = self.structure.run_in_block(self.preprocess_artifact_list,
                                                                    name, True, report_artifact_list,
                                                                    ignore_existing_artifacts)

    def move_artifact(self, path, is_report=False):
        self.out.log("Processing '" + path + "'")
        matches = glob2.glob(path)
        if not matches:
            if not is_report:
                text = "No artifacts found!" + "\nPossible reasons of this error:\n" + \
                       " * Artifact was not created while building the project due to some internal errors\n" + \
                       " * Artifact path was not specified correctly in 'configs.py'"
                raise CiException(text)

            self.out.log("No artifacts found.")

        for matching_path in matches:
            artifact_name = os.path.basename(matching_path)
            destination = os.path.join(self.artifact_dir, artifact_name)
            if not self.settings.no_archive:
                try:
                    make_big_archive(destination, matching_path)
                    if is_report:
                        artifact_path = self.automation_server.artifact_path(self.artifact_dir, artifact_name + ".zip")
                        self.collected_report_artifacts.add(artifact_path)
                    continue
                except OSError:
                    # Single file archiving is not implemented at the moment
                    pass
            try:
                distutils.dir_util.copy_tree(matching_path, destination)
                if is_report:
                    text = "'" + artifact_name + "' is not a file and cannot be reported as an artifact"
                    self.out.log(text)
            except distutils.errors.DistutilsFileError:
                shutil.copyfile(matching_path, destination)
                if is_report:
                    artifact_path = self.automation_server.artifact_path(self.artifact_dir, artifact_name)
                    self.collected_report_artifacts.add(artifact_path)

    @make_block("Collecting artifacts", pass_errors=False)
    def collect_artifacts(self):
        self.reporter.add_block_to_report(self.structure.get_current_block())
        for path in self.report_artifact_list:
            name = "Collecting '" + os.path.basename(path) + "' for report"
            self.structure.run_in_block(self.move_artifact, name, False, path, is_report=True)
        self.reporter.report_artifacts(list(self.collected_report_artifacts))
        for path in self.artifact_list:
            name = "Collecting '" + os.path.basename(path) + "'"
            self.structure.run_in_block(self.move_artifact, name, False, path)

    def clean_artifacts_silently(self):
        try:
            shutil.rmtree(self.artifact_dir)
        except OSError:
            pass
        os.makedirs(self.artifact_dir)
