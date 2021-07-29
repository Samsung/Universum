import os
import pytest

from selenium import webdriver
from selenium.webdriver.firefox.options import Options


config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Dummy", command=["echo", "dummy"])])
"""


@pytest.fixture()
def browser():
    options = Options()
    options.headless = True
    firefox = webdriver.Firefox(options=options)
    yield firefox
    firefox.close()


def test_success(docker_main, browser):
    docker_main.run(config, additional_parameters="--html-log")
    log_path = os.path.join(docker_main.artifact_dir, "log.html")
    assert os.path.exists(log_path)

    browser.get(f"file://{log_path}")
    body_element = browser.find_element_by_tag_name("body")
    body_elements = body_element.find_elements_by_xpath(".//*")
    assert len(body_elements) == 1

    pre_element = body_elements[0]
    assert pre_element.tag_name == "pre"
    assert pre_element.text # will be changed to valid HTML in further commits


def test_no_html_log_requested(docker_main):
    docker_main.run(config)
    log_path = os.path.join(docker_main.artifact_dir, "log.html")
    assert not os.path.exists(log_path)
