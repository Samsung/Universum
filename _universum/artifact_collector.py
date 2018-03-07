# -*- coding: UTF-8 -*-

import codecs
import distutils
from distutils import dir_util, errors
import glob
import os
import shutil

from .ci_exception import CriticalCiException, CiException
from .gravity import Module, Dependency
from .output import needs_output
from .reporter import Reporter
from .structure_handler import needs_structure
from .utils import make_block

__all__ = [
    "ArtifactCollector"
]


@needs_output
@needs_structure
class ArtifactCollector(Module):
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Artifact collection",
                                                     "Parameters of archiving and collecting of build artifacts")

        parser.add_argument("--artifact-dir", "-ad", dest="artifact_dir", metavar="ARTIFACT_DIR",
                            help="Directory to collect artifacts to. Default is 'artifacts'")

        parser.add_argument("--no-archive", action="store_true", dest="no_archive",
                            help="By default all directories noted as artifacts are copied as .zip archives. "
                                 "This option turn archiving off to copy bare directories to artifact directory")

    def __init__(self, settings):
        self.settings = settings
        self.reporter = self.reporter_factory()

        self.artifact_list = []
        self.report_artifact_list = []

        # Needed because of wildcards
        self.collected_report_artifacts = set()

        self.file_list = set()
        self.artifact_dir = settings.artifact_dir

        if not self.artifact_dir:
            self.artifact_dir = os.path.join(os.getcwd(), "artifacts")
        if not os.path.exists(self.artifact_dir):
            os.makedirs(self.artifact_dir)

    def make_file_name(self, name):
        name = name.replace(" ", "_")
        name = name.replace("/", "\\")
        if name.startswith('_'):
            name = name[1:]
        name = os.path.join(self.artifact_dir, name)
        return name

    def create_text_file(self, name):
        try:
            file_name = self.make_file_name(name)

            # File system interaction modules only work with encoded unicode strings
            if isinstance(file_name, unicode):
                encoded_name = file_name.encode("utf-8")
            else:
                encoded_name = str(file_name)

            if file_name not in self.file_list:
                if os.path.exists(encoded_name):
                    text = "File '" + os.path.basename(file_name) + "' already exists in artifact directory." + \
                           "\nPossible reason of this error: previous build artifacts are not cleaned"
                    raise CriticalCiException(text)

            self.file_list.add(file_name)
            self.out.log("Adding file '" + os.path.basename(file_name) + "' to artifact directory...")
            return codecs.open(encoded_name, "a", encoding="utf-8")
        except IOError as e:
            raise CiException("The following error occurred while working with file: " + unicode(e))

    def preprocess_artifact_list(self, artifact_list):
        """
        Check artifacts for existence; remove if required; raise exception otherwise; sort and remove duplicates
        :param artifact_list: list of dictionaries with keys 'path' (for path) and 'clean' to clean it before build
        :return: sorted list of checked paths (including duplicates and wildcards)
        """
        dir_list = set()
        for item in artifact_list:
            # Check existence in place: wildcards applied
            matches = glob.glob(item["path"])
            if matches:
                if item["clean"]:
                    for matching_path in matches:
                        try:
                            os.remove(matching_path)
                        except OSError as e:
                            if "Is a directory" not in e:
                                raise
                            shutil.rmtree(matching_path)
                else:
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

    @make_block("Setting and preprocessing artifacts according to configs")
    def set_and_clean_artifacts(self, path_list):
        self.artifact_list = self.preprocess_artifact_list(path_list)

    @make_block("Setting and preprocessing artifacts to be mentioned in report")
    def set_and_clean_report_artifacts(self, path_list):
        self.report_artifact_list = self.preprocess_artifact_list(path_list)

    def move_artifact(self, path, is_report=False):
        self.out.log("Processing '" + path + "'")
        matches = glob.glob(path)
        if not matches:
            if is_report:
                self.out.log("No artifacts found.")
                return
            else:
                text = "No artifacts found!" + "\nPossible reasons of this error:\n" + \
                       " * Artifact was not created while building the project due to some internal errors\n" + \
                       " * Artifact path was not specified correctly in 'configs.py'"
                raise CiException(text)

        for matching_path in matches:
            artifact_name = os.path.basename(matching_path)
            destination = os.path.join(self.artifact_dir, artifact_name)
            if not self.settings.no_archive:
                try:
                    shutil.make_archive(destination, "zip", matching_path)
                    if is_report:
                        self.collected_report_artifacts.add(artifact_name + ".zip")
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
                    self.collected_report_artifacts.add(artifact_name)

    @make_block("Collecting artifacts", pass_errors=False)
    def collect_artifacts(self):
        self.reporter.add_block_to_report(self.structure.get_current_block())
        for path in self.report_artifact_list:
            name = "Collecting '" + os.path.basename(path) + "' for report"
            self.structure.run_in_block(self.move_artifact, name, False, path, is_report=True)
        self.reporter.report_artifacts(self.artifact_dir, list(self.collected_report_artifacts))
        for path in self.artifact_list:
            name = "Collecting '" + os.path.basename(path) + "'"
            self.structure.run_in_block(self.move_artifact, name, False, path)
