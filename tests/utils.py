import copy
import datetime
import os
import random
import socket
import string
import sys

import httpretty
import py

from universum import submit, poll, main, github_handler, nonci, __main__
from universum.lib import gravity
from universum.lib.module_arguments import ModuleNamespace

from .thirdparty.pyfeed.rfc3339 import tf_from_timestamp
from . import default_args

__all__ = [
    "python",
    "python_version",
    "Params",
    "reuse_docker_containers",
    "randomize_name",
    "get_open_port",
    "python_time_from_rfc3339_time",
    "is_container_outdated",
    "create_empty_settings",
    "simple_test_config",
    "BaseVcsClient",
    "BaseTestEnvironment",
    "LocalTestEnvironment"
]

PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
PYTHON = "python" + PYTHON_VERSION


def python():
    return PYTHON


def python_version():
    return PYTHON_VERSION


class Params:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def reuse_docker_containers():
    return ("PYCHARM_HOSTED" in os.environ) or ("REUSE_DOCKER_CONTAINERS" in os.environ)


def randomize_name(name):
    return name + "-" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def get_open_port():
    temp = socket.socket()
    temp.bind(("", 0))
    result = temp.getsockname()[1]
    temp.close()
    return result


def python_time_from_rfc3339_time(rfc3339_time):
    return tf_from_timestamp(rfc3339_time)


def is_container_outdated(container):
    created = python_time_from_rfc3339_time(container.attrs["Created"])
    delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(created)
    if abs(delta).days > 7:
        return True
    return False


def create_empty_settings(test_type):
    if test_type == "poll":
        main_class = poll.Poll
    elif test_type == "submit":
        main_class = submit.Submit
    elif test_type == "github-handler":
        main_class = github_handler.GithubHandler
    elif test_type == "main":
        main_class = main.Main
    elif test_type == "nonci":
        main_class = nonci.Nonci
    else:
        assert False, "create_empty_settings expects test_type parameter to be poll, submit, main or nonci"
    argument_parser = default_args.ArgParserWithDefault()
    argument_parser.set_defaults(main_class=main_class)
    gravity.define_arguments_recursive(main_class, argument_parser)
    settings = argument_parser.parse_args([])
    return settings


simple_test_config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Test configuration", command=["ls", "-la"])])
"""


class BaseVcsClient:
    def __init__(self):
        self.root_directory: py.path.local
        self.repo_file: py.path.local

    def get_last_change(self):
        raise NotImplementedError()

    def file_present(self, file_path: str) -> bool:
        raise NotImplementedError()

    def text_in_file(self, text: str, file_path: str) -> bool:
        raise NotImplementedError()

    def make_a_change(self) -> str:
        raise NotImplementedError()


class HttpChecker:
    @staticmethod
    def assert_request_with_query(query, ensure):
        queries = []
        for request in httpretty.httpretty.latest_requests:
            if request.querystring == query:
                if ensure:
                    return
                assert False, f"Query string was found in calls to http server.\n" \
                              f"Expected: {query}\nActual:{str(queries)}"
            queries.append(request.querystring)

        if ensure:
            assert False, f"Query string is not found in calls to http server.\n" \
                          f"Expected: {query}\nActual:{str(queries)}"

    @staticmethod
    def assert_request_was_made(query):
        HttpChecker.assert_request_with_query(query, ensure=True)

    @staticmethod
    def assert_request_was_not_made(query):
        HttpChecker.assert_request_with_query(query, ensure=False)

    @staticmethod
    def assert_request_contained(key, value, target):
        results = []
        for request in httpretty.httpretty.latest_requests:
            if target == "query param":
                check_target = request.querystring
            elif target == "header":
                check_target = request.headers
            elif target == "body field":
                check_target = request.parsed_body
            else:
                assert False, f"This type of check ('{target}') is not implemented"

            if key in check_target:
                if (target == "query param") and (value in check_target[key]):
                    return
                if check_target[key] == value:
                    return
                results.append(check_target[key])

        if not results:
            text = f"No requests with {target} '{key}' found in calls to http server"
        else:
            text = f"No requests with {target} '{key}' set to '{value}' found in calls to http server.\n"
            text += f"However, requests with following values were made: {results}"
        assert False, text

    @staticmethod
    def assert_request_query_contained(key, value):
        HttpChecker.assert_request_contained(key, value, "query param")

    @staticmethod
    def assert_request_headers_contained(key, value):
        HttpChecker.assert_request_contained(key, value, "header")

    @staticmethod
    def assert_request_body_contained(key, value):
        HttpChecker.assert_request_contained(key, value, "body field")


class BaseTestEnvironment:
    def __init__(self, client: BaseVcsClient, directory: py.path.local, test_type: str, db_file: str):
        self.temp_dir: py.path.local = directory
        self.vcs_client = client
        self.settings: ModuleNamespace = create_empty_settings(test_type)

        if test_type == "poll":
            self.settings.Poll.db_file = db_file
            self.settings.JenkinsServerForTrigger.trigger_url = "https://localhost/?cl=%s"
            self.settings.AutomationServer.type = "jenkins"
            self.settings.ProjectDirectory.project_root = str(self.temp_dir.mkdir("project_root"))
        elif test_type == "submit":
            self.settings.Submit.commit_message = "Test CL"
            # For submitter, the main working dir (project_root) should be the root
            # of the VCS workspace/client
            self.settings.ProjectDirectory.project_root = str(self.vcs_client.root_directory)
        elif test_type in ("main", "nonci"):
            self.configs_file = self.temp_dir.join("configs.py")
            self.configs_file.write(simple_test_config)
            self.settings.Launcher.config_path = str(self.configs_file)
            self.artifact_dir = self.temp_dir.mkdir("artifacts")
            self.settings.ArtifactCollector.artifact_dir = str(self.artifact_dir)
            # The project_root directory must not exist before launching main
            self.settings.ProjectDirectory.project_root = str(self.temp_dir.join("project_root"))
            if test_type == "nonci":
                self.temp_dir.mkdir("project_root")
            self.settings.Launcher.output = "console"
            self.settings.AutomationServer.type = "local"
        self.settings.Output.type = "term"

    def run(self, expect_failure: bool = False) -> None:
        settings = copy.deepcopy(self.settings)
        if expect_failure:
            assert __main__.run(settings)
        else:
            assert not __main__.run(settings)

    def run_with_http_server(self,
                             expect_failure: bool = False,
                             url: str = "https://localhost/",
                             method: str = "GET",
                             status: str = "200") -> HttpChecker:
        httpretty.reset()
        httpretty.enable()
        if method == "GET":
            hmethod = httpretty.GET
        elif method == "POST":
            hmethod = httpretty.POST
        else:
            hmethod = httpretty.PATCH
        httpretty.register_uri(hmethod, url, status=status)

        try:
            self.run(expect_failure)
        finally:
            httpretty.disable()

        return HttpChecker()


class LocalTestEnvironment(BaseTestEnvironment):
    def __init__(self, directory, test_type):
        super().__init__(BaseVcsClient(), directory, test_type, "")
