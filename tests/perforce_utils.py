# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import datetime
import time

import P4
import docker
import pytest
from requests.exceptions import ReadTimeout

from . import utils
from .thirdparty.pyfeed.rfc3339 import tf_from_timestamp

p4_image_name = "perforce"
p4_user = "p4user"
p4_password = "abcdefgh123456"
p4_create_timeout = 60  # seconds
p4_start_timeout = 10  # seconds


def python_time_from_rfc3339_time(rfc3339_time):
    return tf_from_timestamp(rfc3339_time)


def ignore_p4_exception(ignore_if, func, *args, **kwargs):
    result = None
    try:
        result = func(*args, **kwargs)
    except P4.P4Exception as e:
        if ignore_if not in unicode(e):
            raise
    return result


def is_p4_container_healthy(container, server_name, polling_start):
    logs = container.logs(timestamps=True)

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
        timestamp = python_time_from_rfc3339_time(rfc3339_time)
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
        created = python_time_from_rfc3339_time(container.attrs["Created"])
        delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(created)
        if abs(delta).days > 7:
            return False
    except docker.errors.NotFound:
        return False

    if container.status == "running":
        started_at = python_time_from_rfc3339_time(container.attrs["State"]["StartedAt"])
        if is_p4_container_healthy(container, name, started_at):
            return True

    container.start()

    if not wait_p4_container_start(client, name, p4_start_timeout):
        return False

    return True


def create_new_p4_container(request, client, name, params):
    image = utils.get_image(request, client, params, p4_image_name)
    client.containers.run(image,
                          name=name,
                          detach=True,
                          ports={"1666/tcp": ("127.0.0.1", None)},
                          environment={"SERVER_NAME": name, "P4USER": p4_user, "P4PASSWD": p4_password})

    if not wait_p4_container_start(client, name, p4_create_timeout):
        request.raiseerror("Timeout on waiting perforce server to start.")


@pytest.fixture(scope="session")
def docker_perforce(request, docker_registry_params):
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

            create_new_p4_container(request, client, unique_id, docker_registry_params)

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
    p4 = P4.P4()
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
        work_dir = tmpdir.ensure("working", dir=True)
        root = tmpdir.ensure("workspace", dir=True)

        client = p4.fetch_client(client_name)
        client["Root"] = str(root)
        client["View"] = [depot + " //" + client_name + "/..."]
        p4.save_client(client)
        client_created = True
        p4.client = client_name

        ignore_p4_exception("no such file(s).", p4.run_sync, "//depot/...")
        tmpfile = root.join("test.txt")

        p4.run("add", str(tmpfile))
        p4.run("edit", str(tmpfile))
        tmpfile.write("Test path" + str(tmpfile))

        change = p4.run_change("-o")[0]
        change["Description"] = "Test submit"
        commited_change = p4.run_submit(change)

        yield utils.Params(p4=p4,
                           client_name=client_name,
                           commited_change=commited_change,
                           depot=depot,
                           work_dir=work_dir,
                           workspace_root=root,
                           workspace_file=tmpfile,
                           tmpfile=tmpfile)

    finally:
        if client_created:
            remainig_shelves = p4.run_changes("-s", "shelved")
            for item in remainig_shelves:
                p4.run_shelve("-dfc", item["change"])
            p4.delete_client("-f", client_name)
