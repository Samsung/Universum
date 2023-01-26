# pylint: disable = redefined-outer-name, too-many-locals

import time
import pathlib

import docker
import pytest
from P4 import P4, P4Exception
from requests.exceptions import ReadTimeout

from . import utils


p4_user = "p4user"
p4_password = "abcdefgh123456"
p4_create_timeout = 60  # seconds
p4_start_timeout = 10  # seconds


def ignore_p4_exception(ignore_if, func, *args, **kwargs):
    result = None
    try:
        result = func(*args, **kwargs)
    except P4Exception as e:
        if ignore_if not in str(e):
            raise
    return result


def is_p4_container_healthy(container, server_name, polling_start):
    # Server log contains unicode paths, we have to convert raw str to unicode type
    logs = container.logs(timestamps=True).decode("utf-8", "replace")

    if container.status != "running":
        return False

    if logs.find("ServerID: " + server_name) == -1:
        return False

    for log in logs.split("\n"):

        if " " not in log:
            continue

        rfc3339_time, text = log.split(" ", 1)
        if not all(x in text for x in ["Started ", server_name, " p4d service."]):
            continue

        # check if "Started <server name> p4d service" is logged after we
        # started container, but with some room for cases when check is
        # called with some delay after start. We give it 5 seconds at max.
        timestamp = utils.python_time_from_rfc3339_time(rfc3339_time)
        if timestamp + 5 > polling_start:
            return True

    return False


def wait_p4_container_start(client, name, timeout):
    start_time = time.time()
    finish_time = start_time + timeout

    while True:
        # We must get new instance on each iteration, because status is not updated otherwise
        container = client.containers.get(name)
        if is_p4_container_healthy(container, name, start_time):
            break
        if time.time() > finish_time:
            return False
        time.sleep(1)

    return True


def ensure_p4_container_started(client, name):
    try:
        container = client.containers.get(name)
        # if the container is too old, ignore it
        if utils.is_container_outdated(container):
            return False
    except docker.errors.NotFound:
        return False

    if container.status == "running":
        started_at = utils.python_time_from_rfc3339_time(container.attrs["State"]["StartedAt"])
        if is_p4_container_healthy(container, name, started_at):
            return True

    container.start()

    if not wait_p4_container_start(client, name, p4_start_timeout):
        return False

    return True


def create_new_p4_container(request, client, name):
    image = client.images.get("perforce")
    client.containers.run(image,
                          name=name,
                          detach=True,
                          ports={"1666/tcp": ("127.0.0.1", None)},
                          environment={"SERVER_NAME": name, "P4USER": p4_user, "P4PASSWD": p4_password})

    if not wait_p4_container_start(client, name, p4_create_timeout):
        request.raiseerror("Timeout on waiting perforce server to start.")


class PerfoceDockerContainer:
    def __init__(self, container_id: str, port: str, user: str, password: str):
        self.container_id: str = container_id
        self.port: str = port
        self.user: str = user
        self.password: str = password


@pytest.fixture(scope="session")
def docker_perforce(request):
    container = None
    client = docker.from_env()

    unique_id = utils.randomize_name("ci_test_perforce")
    if utils.reuse_docker_containers():
        unique_id = request.config.cache.get("ci_test/perforce_container", unique_id)

    try:
        if not ensure_p4_container_started(client, unique_id):
            # remove old unhealthy container and create new one
            try:
                client.containers.get(unique_id).remove(force=True)
            except docker.errors.NotFound:
                pass

            create_new_p4_container(request, client, unique_id)

        container = client.containers.get(unique_id)

        port_number = container.attrs["NetworkSettings"]["Ports"]["1666/tcp"][0]["HostPort"]

        yield PerfoceDockerContainer(container_id=unique_id,  # We do not use this ID anywhere
                                     port="127.0.0.1:" + str(port_number),
                                     user=p4_user,
                                     password=p4_password)
    except:
        if container is not None:
            container.remove(force=True)
            container = None
        raise

    finally:
        if container is not None:
            if utils.reuse_docker_containers():
                request.config.cache.set("ci_test/perforce_container", unique_id)
            else:
                try:
                    container.remove(force=True)
                except ReadTimeout:
                    pass


class PerforceConnection:
    def __init__(self, p4: P4, server: PerfoceDockerContainer):
        self.p4: P4 = p4
        self.server: PerfoceDockerContainer = server


@pytest.fixture()
def perforce_connection(request, docker_perforce: PerfoceDockerContainer):
    p4 = P4()
    p4.port = docker_perforce.port
    p4.user = docker_perforce.user
    p4.password = docker_perforce.password
    p4.connect()
    p4.run_login()
    yield PerforceConnection(p4=p4, server=docker_perforce)
    p4.disconnect()


class PerforceWorkspace(utils.BaseVcsClient):
    def __init__(self, connection: PerforceConnection, directory: pathlib.Path):
        super().__init__()
        self.root_directory = directory.joinpath("workspace")
        self.root_directory.mkdir()
        self.repo_file = self.root_directory.joinpath("writeable_file.txt")

        self.nonwritable_file: pathlib.Path = self.root_directory.joinpath("usual_file.txt")

        self.server: PerfoceDockerContainer = connection.server
        self.client_created: bool = False
        self.client_name: str = "test_workspace"
        self.depot: str = "//depot/..."
        self.p4: P4 = connection.p4

    def setup(self) -> None:
        client = self.p4.fetch_client(self.client_name)
        client["Root"] = str(self.root_directory)
        client["View"] = [self.depot + " //" + self.client_name + "/..."]
        self.p4.save_client(client)
        self.client_created = True
        self.p4.client = self.client_name

        ignore_p4_exception("no such file(s).", self.p4.run_sync, self.depot)

        self.p4.run("add", str(self.nonwritable_file))
        self.p4.run("edit", str(self.nonwritable_file))
        self.nonwritable_file.write("File " + str(self.nonwritable_file) + " has no special modifiers")

        self.p4.run("add", "-t", "+w", str(self.repo_file))
        self.repo_file.write("File " + str(self.repo_file) + " is always writable")

        change = self.p4.run_change("-o")[0]
        change["Description"] = "Test submit"
        self.p4.run_submit(change)

        permissions = self.p4.fetch_protect()
        permissions['Protections'] = [
            'write user * * //...',
            'list user * * -//spec/...',
            'super user p4user * //...',                         # first three rows are default
            '=write user p4user * -//depot/write-protected/...'  # prohibit p4user to submit changes to this branch
        ]
        self.p4.save_protect(permissions)

        triggers = {'Triggers': [
            'test.check change-submit //depot/trigger-protected/... "false"'  # trigger to prevent any submits to this branch
        ]}
        self.p4.save_triggers(triggers)

    def create_file(self, file_name: str) -> pathlib.Path:
        p4_new_file = self.root_directory.joinpath(file_name)
        p4_new_file.write("This is unchanged line 1\nThis is unchanged line 2")
        self.p4.run("add", str(p4_new_file))

        change = self.p4.run_change("-o")[0]
        change["Description"] = "Add a file for checks"
        self.p4.run_submit(change)
        return p4_new_file

    def delete_file(self, file_name: str) -> None:
        self.p4.run("delete", self.depot + file_name)
        change = self.p4.run_change("-o")[0]
        change["Description"] = "Delete created file"
        self.p4.run_submit(change)

    def shelve_file(self, file: pathlib.Path, content: str, shelve_cl=None) -> str:
        if not shelve_cl:
            change = self.p4.fetch_change()
            change["Description"] = "This is a shelved CL"
            shelve_cl = self.p4.save_change(change)[0].split()[1]

        self.p4.run_edit("-c", shelve_cl, str(file))
        file.write(content)
        self.p4.run_shelve("-fc", shelve_cl)
        self.p4.run_revert("-c", shelve_cl, str(file))
        return shelve_cl

    def get_last_change(self) -> str:
        changes = self.p4.run_changes("-s", "submitted", "-m1", self.depot)
        return changes[0]["change"]

    def text_in_file(self, text: str, file_path: str) -> bool:
        return text in self.p4.run_print(file_path)[-1]

    def file_present(self, file_path: str) -> bool:
        try:
            self.p4.run_files("-e", file_path)
            return True
        except P4Exception as e:
            if not e.warnings:
                raise
            if "no such file(s)" not in e.warnings[0]:
                raise
            return False

    def make_a_change(self) -> str:
        tmpfile = self.repo_file
        self.p4.run("edit", str(tmpfile))
        tmpfile.write("Change #1 " + str(tmpfile))

        change = self.p4.run_change("-o")[0]
        change["Description"] = "Test submit #1"

        committed_change = self.p4.run_submit(change)

        cl = next((x["submittedChange"] for x in committed_change if "submittedChange" in x))
        return cl

    def cleanup(self) -> None:
        if self.client_created:
            remaining_shelves = self.p4.run_changes("-s", "shelved")
            for item in remaining_shelves:
                self.p4.run_shelve("-dfc", item["change"])
            self.p4.delete_client("-f", self.client_name)


@pytest.fixture()
def perforce_workspace(request, perforce_connection: PerforceConnection, tmp_path: pathlib.Path):
    workspace = PerforceWorkspace(perforce_connection, tmp_path)
    try:
        workspace.setup()
        yield workspace
    finally:
        workspace.cleanup()


class P4TestEnvironment(utils.BaseTestEnvironment):
    def __init__(self, perforce_workspace: PerforceWorkspace, directory: pathlib.Path, test_type: str):
        db_file = directory.joinpath("p4poll.json")
        super().__init__(perforce_workspace, directory, test_type, str(db_file))
        self.vcs_client: PerforceWorkspace

        self.client_name: str = "p4_disposable_workspace"

        self.settings.Vcs.type = "p4"
        self.settings.PerforceVcs.port = perforce_workspace.server.port
        self.settings.PerforceVcs.user = perforce_workspace.server.user
        self.settings.PerforceVcs.password = perforce_workspace.server.password
        try:
            self.settings.PerforceMainVcs.client = self.client_name
            self.settings.PerforceMainVcs.force_clean = True
        except AttributeError:
            pass
        try:
            self.settings.PerforceWithMappings.project_depot_path = perforce_workspace.depot
        except AttributeError:
            pass
        try:
            self.settings.PerforceSubmitVcs.client = perforce_workspace.client_name
        except AttributeError:
            pass

    def shelve_config(self, config: str) -> None:
        shelve_cl = self.vcs_client.shelve_file(self.vcs_client.repo_file, config)
        settings = self.settings
        settings.PerforceMainVcs.shelve_cls = [shelve_cl]
        settings.Launcher.config_path = self.vcs_client.repo_file.basename
