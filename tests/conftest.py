# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import getpass
from pwd import getpwnam
import os

import docker
import git
import httpretty
import pytest
import mock
from . import utils

pytest_plugins = ['tests.perforce_utils']


def pytest_addoption(parser):
    parser.addoption("--docker-registry-url", action="store", default=None,
                     help="Fully-qualified name of docker registry to pull images from. "
                          "Optional, images are built if registry is not specified")
    parser.addoption("--docker-registry-login", action="store", default=None,
                     help="User name to login to registry")
    parser.addoption("--docker-registry-password", action="store", default=None,
                     help="Password to login to registry")


@pytest.fixture(scope="session")
def docker_registry_params(request):
    url = request.config.getoption("--docker-registry-url")
    login = request.config.getoption("--docker-registry-login")
    password = request.config.getoption("--docker-registry-password")

    if not all((url, login, password)):
        return None

    return utils.Params(url=url, login=login, password=password)


class FuzzyCallChecker(object):
    def __init__(self, mock_object):
        self.mock_object = mock_object

    def _assertion_message(self, string_to_find):
        return '\nExpected param: %s\nActual list: %r' % (string_to_find, self.mock_object.mock_calls)

    def _find_call_with_param(self, string_param):
        for call in self.mock_object.mock_calls:
            _, args, _ = call
            for arg in args:
                if string_param in arg:
                    return True
        # return explicit False
        return False

    def assert_has_calls_with_param(self, string_param):
        assert self._find_call_with_param(string_param), 'String parameter is not found in call list. %s' \
                                                         % (self._assertion_message(string_param))

    def assert_absent_calls_with_param(self, string_param):
        assert not self._find_call_with_param(string_param), 'String parameter is found in call list, ' \
                                                             'but is not expected to be found.%s' \
                                                             % (self._assertion_message(string_param))


@pytest.fixture()
def stdout_checker(request):
    with mock.patch('_universum.local_driver.stdout') as logging_mock:
        result = FuzzyCallChecker(logging_mock)
        yield result


@pytest.fixture()
def log_exception_checker(request):
    with mock.patch('_universum.local_driver.LocalOutput.log_exception') as logging_mock:
        result = FuzzyCallChecker(logging_mock)
        yield result


class HttpChecker(object):
    @staticmethod
    def assert_request_was_made(query):
        queries = []
        for request in httpretty.httpretty.latest_requests:
            if request.querystring == query:
                return
            queries.append(request.querystring)

        assert False, 'Query string is not found in calls to http server.\nExpected: %s\nActual: %r' % (query, queries)


@pytest.fixture()
def http_request_checker(request):
    httpretty.enable()
    httpretty.register_uri(httpretty.GET, "https://localhost/")
    yield HttpChecker()
    httpretty.disable()
    httpretty.reset()


class CommandRunner(object):
    def __init__(self, client, container, bound_dir):
        self._client = client
        self._container = container
        self._bound_dir = bound_dir

    def get_working_directory(self):
        return self._bound_dir

    def exit(self):
        user_id = getpwnam(getpass.getuser()).pw_uid
        self._container.exec_run("chown -R {} {}".format(user_id, self._bound_dir))
        self._container.stop(timeout=0)

    def _run_and_check(self, cmd, result):
        process_id = self._client.api.exec_create(self._container.id, cmd)
        print "$ " + cmd
        log = self._client.api.exec_start(process_id)
        print log

        exit_code = self._client.api.exec_inspect(process_id)['ExitCode']
        if result:
            assert exit_code == 0
        else:
            assert exit_code != 0

        return log

    def assert_success(self, cmd):
        return self._run_and_check(cmd, True)

    def assert_failure(self, cmd):
        return self._run_and_check(cmd, False)


@pytest.fixture()
def command_runner(request, docker_registry_params):
    client = docker.from_env()
    container = None
    runner = None
    bind_dir = "/host"
    try:
        try:
            image = utils.get_image(request, client, docker_registry_params, "pythonp4")
            container = client.containers.run(image,
                                              command="sleep infinity",
                                              volumes={os.getcwd(): {'bind': bind_dir, 'mode': 'rw'}},
                                              network_mode='host',
                                              auto_remove=True,
                                              detach=True)
            runner = CommandRunner(client, container, bind_dir)
            yield runner
        finally:
            if runner is not None:
                runner.exit()
    except:
        if container is not None:
            container.remove(force=True)
        raise


class GitServer(object):
    def __init__(self, working_directory, branch_name):
        self.url = "file://" + unicode(working_directory)
        self.target_branch = branch_name
        self.target_file = "readme.txt"

        self._working_directory = working_directory
        self._repo = git.Repo.init(unicode(working_directory))
        configurator = self._repo.config_writer()
        configurator.set_value("user", "name", "Testing user")
        configurator.set_value("user", "email", "some@email.com")
        self._file = self._working_directory.join(self.target_file)
        self._file.write("")

        self._repo.index.add([unicode(self._file)])
        self._repo.index.commit("initial commit")
        self._commit_count = 0

        self._branch = self._repo.create_head(branch_name)

    def make_a_change(self):
        self._branch.checkout()

        self._file.write("One more line\n")
        self._commit_count += 1

        self._repo.index.add([unicode(self._file)])
        change = unicode(self._repo.index.commit("add line " + unicode(self._commit_count)))
        self._repo.heads.master.checkout()
        return change

    def commit_new_file(self):
        """ Make a mergeble commit """
        self._commit_count += 1
        test_file = self._working_directory.join("test%s.txt" % self._commit_count)
        test_file.write("Commit number #%s" % (self._commit_count))
        self._repo.index.add([unicode(test_file)])
        return unicode(self._repo.index.commit("Add file " + unicode(self._commit_count)))

    def make_branch(self, name):
        self._repo.git.checkout("-b", name)

    def switch_branch(self, name):
        self._repo.git.checkout(name)

    def merge_branch(self, name, fast_forward):
        """
        Merge specified branch to the current
        :param name: Name of merged branch
        :param fast_forward: Boolean. Try to use fast forward or create a merge commit on merge
        :return: None
        """
        if fast_forward:
            cmd_option = "--ff-only"
        else:
            cmd_option = "--no-ff"
        self._repo.git.merge(cmd_option, name)

    def get_last_commit(self):
        return self._repo.git.log('-n1', pretty='format:"%H"').replace('"', '')


@pytest.fixture()
def git_server(tmpdir):
    directory = tmpdir.mkdir("server")
    yield GitServer(directory, "testing")


def check_output((out, err)):
    assert not err, "Stderr detected!"
    for text in ["Traceback", "Exception"]:
        assert text not in out, text + " detected in stdout!"


# pylint: disable = protected-access
@pytest.fixture(autouse=True)
def detect_fails(capsys):
    yield capsys
    check_output(capsys.readouterr())
    check_output(capsys._outerr)
