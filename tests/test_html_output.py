# pylint: disable = redefined-outer-name

import os
import pytest

from selenium import webdriver
from selenium.webdriver.firefox.options import Options


config = """
from universum.configuration_support import Configuration

success_step = Configuration([dict(name="Success step", command=["echo", "success"])])
failed_step = Configuration([dict(name="Failed step", command=["./non_existing_script.sh"])])
partially_success_step = Configuration([dict(name="Partially success step: ")])
all_success_step = Configuration([dict(name="All success step: ")])
all_failed_step = Configuration([dict(name="All failed step: ")])

configs = \
    success_step + \
    failed_step + \
    partially_success_step * (success_step + failed_step) + \
    all_success_step * (success_step + success_step) + \
    all_failed_step * (failed_step + failed_step)
"""


@pytest.fixture()
def browser():
    options = Options()
    options.headless = True
    firefox = webdriver.Firefox(options=options)
    yield firefox
    firefox.close()


def test_success(docker_main_and_nonci, browser):
    docker_main_and_nonci.run(config, additional_parameters="--html-log")
    check_html_log(docker_main_and_nonci.artifact_dir, browser)


def test_success_clean_build(docker_main, browser):
    docker_main.run(config, additional_parameters="--html-log --clean-build")
    check_html_log(docker_main.artifact_dir, browser)


def test_no_html_log_requested(docker_main_and_nonci):
    docker_main_and_nonci.run(config)
    log_path = os.path.join(docker_main_and_nonci.artifact_dir, "log.html")
    assert not os.path.exists(log_path)


def check_html_log(artifact_dir, browser):
    log_path = os.path.join(artifact_dir, "log.html")
    assert os.path.exists(log_path)

    browser.get(f"file://{log_path}")
    body_element = browser.find_element_by_tag_name("body")
    body_elements = body_element.find_elements_by_xpath(".//*")
    assert len(body_elements) == 1

    pre_element = body_elements[0]
    assert pre_element.tag_name == "pre"
    assert pre_element.text # will be changed to valid HTML in further commits
