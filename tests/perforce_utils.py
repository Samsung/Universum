# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name, too-many-locals

import time

from P4 import P4, P4Exception
import docker
import pytest
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
        if ignore_if not in unicode(e):
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
        if not all(x in text for x in ["Started", server_name, "p4d service."]):
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


@pytest.fixture(scope="session")
def docker_perforce(request):
    container = None
    client = docker.from_env()

    unique_id = utils.randomize_name("ci_test_perforce")
    if utils.is_pycharm():
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

        yield utils.Params(container_id=unique_id,
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
            if utils.is_pycharm():
                request.config.cache.set("ci_test/perforce_container", unique_id)
            else:
                try:
                    container.remove(force=True)
                except ReadTimeout:
                    pass


@pytest.fixture()
def perforce_connection(request, docker_perforce):
    p4 = P4()
    p4.port = docker_perforce.port
    p4.user = docker_perforce.user
    p4.password = docker_perforce.password
    p4.connect()
    p4.run_login()
    yield p4
    p4.disconnect()


@pytest.fixture()
def perforce_workspace(request, perforce_connection, tmpdir):
    client_name = "test_workspace"
    p4 = perforce_connection
    client_created = False
    depot = "//depot/..."

    try:
        root = tmpdir.mkdir("workspace")

        client = p4.fetch_client(client_name)
        client["Root"] = str(root)
        client["View"] = [depot + " //" + client_name + "/..."]
        p4.save_client(client)
        client_created = True
        p4.client = client_name

        ignore_p4_exception("no such file(s).", p4.run_sync, "//depot/...")

        usual_file = root.join("usual_file.txt")
        p4.run("add", str(usual_file))
        p4.run("edit", str(usual_file))
        usual_file.write("File " + str(usual_file) + " has no special modifiers")

        writeable_file = root.join("writeable_file.txt")
        p4.run("add", "-t", "+w", str(writeable_file))
        writeable_file.write("File " + str(writeable_file) + " is always writable")

        change = p4.run_change("-o")[0]
        change["Description"] = "Test submit"
        p4.run_submit(change)

        permissions = p4.fetch_protect()
        permissions['Protections'] = [
            'write user * * //...',
            'list user * * -//spec/...',
            'super user p4user * //...',
            '=write user p4user * -//depot/protected/...'
        ]
        p4.save_protect(permissions)

        yield utils.Params(p4=p4,
                           client_name=client_name,
                           depot=depot,
                           root_directory=root,
                           repo_file=writeable_file,
                           nonwritable_file=usual_file)

    finally:
        if client_created:
            remaining_shelves = p4.run_changes("-s", "shelved")
            for item in remaining_shelves:
                p4.run_shelve("-dfc", item["change"])
            p4.delete_client("-f", client_name)


class P4Environment(utils.TestEnvironment):
    def __init__(self, perforce_workspace, directory, test_type):
        db_file = directory.join("p4poll.json")
        self.db_file = unicode(db_file)
        self.vcs_cooking_dir = perforce_workspace.root_directory
        self.repo_file = perforce_workspace.repo_file
        self.nonwritable_file = perforce_workspace.nonwritable_file
        self.p4 = perforce_workspace.p4
        self.depot = perforce_workspace.depot
        self.client_name = "p4_disposable_workspace"
        super(P4Environment, self).__init__(directory, test_type)

        self.settings.Vcs.type = "p4"
        self.settings.PerforceVcs.port = perforce_workspace.p4.port
        self.settings.PerforceVcs.user = perforce_workspace.p4.user
        self.settings.PerforceVcs.password = perforce_workspace.p4.password
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

    def get_last_change(self):
        changes = self.p4.run_changes("-s", "submitted", "-m1", self.depot)
        return changes[0]["change"]

    def file_present(self, file_path):
        try:
            self.p4.run_files("-e", file_path)
            return True
        except P4Exception as e:
            if not e.warnings:
                raise
            if "no such file(s)" not in e.warnings[0]:
                raise
            return False

    def text_in_file(self, text, file_path):
        return text in self.p4.run_print(file_path)[-1]

    def make_a_change(self):
        tmpfile = self.repo_file
        self.p4.run("edit", str(tmpfile))
        tmpfile.write("Change #1 " + str(tmpfile))

        change = self.p4.run_change("-o")[0]
        change["Description"] = "Test submit #1"

        committed_change = self.p4.run_submit(change)

        cl = next((x["submittedChange"] for x in committed_change if "submittedChange" in x))
        return cl
