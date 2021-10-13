# pylint: disable = redefined-outer-name

import os
import re
import pytest

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webelement import FirefoxWebElement

from . import utils


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


def create_environment(test_type, tmpdir):
    env = utils.LocalTestEnvironment(tmpdir, test_type)
    env.configs_file.write(config)
    env.settings.Output.html_log = True

    if test_type == "main":
        env.settings.Vcs.type = "none"
        env.settings.LocalMainVcs.source_dir = str(tmpdir.mkdir('work_dir'))

    return env


@pytest.fixture(params=["main", "nonci"])
def environment_main_and_nonci(request, tmpdir):
    yield create_environment(request.param, tmpdir)


@pytest.fixture()
def browser():
    options = Options()
    options.headless = True
    firefox = webdriver.Firefox(options=options)
    yield firefox
    firefox.close()


def test_success(environment_main_and_nonci, browser):
    environment_main_and_nonci.run()
    check_html_log(environment_main_and_nonci.artifact_dir, browser)


def test_success_clean_build(tmpdir, browser):
    env = create_environment("main", tmpdir)
    env.settings.Main.clean_build = True
    env.run()
    check_html_log(env.artifact_dir, browser)


def test_no_html_log_requested(environment_main_and_nonci):
    environment_main_and_nonci.settings.Output.html_log = False
    environment_main_and_nonci.run()
    log_path = os.path.join(environment_main_and_nonci.artifact_dir, "log.html")
    assert not os.path.exists(log_path)


def check_html_log(artifact_dir, browser):
    log_path = os.path.join(artifact_dir, "log.html")
    assert os.path.exists(log_path)

    browser.get(f"file://{log_path}")
    html_body = browser.find_element_by_tag_name("body")
    body_elements = html_body.find_elements_by_xpath("./*")
    assert len(body_elements) == 1
    assert body_elements[0].tag_name == "pre"

    pre_element = TestElement.create(body_elements[0])
    steps_section = pre_element.get_section_by_name("Executing build steps")
    steps_body = steps_section.get_section_body()

    check_step_collapsed(steps_section, steps_body)
    steps_section.click()
    check_step_not_collapsed(steps_section, steps_body)
    check_sections_indentation(steps_section)
    check_text_coloring(get_page_style(browser), steps_section)
    steps_section.click()
    check_step_collapsed(steps_section, steps_body)


def check_sections_indentation(steps_section):
    steps_body = steps_section.get_section_body()
    step_lvl1_first = steps_body.get_section_by_name("Failed step")
    step_lvl1_second = steps_body.get_section_by_name("Partially success step")
    assert step_lvl1_first.indent == step_lvl1_second.indent

    step_lvl1_second.click()
    step_lvl1_body = step_lvl1_second.get_section_body()
    step_lvl2_first = step_lvl1_body.get_section_by_name("Success step")
    step_lvl2_second = step_lvl1_body.get_section_by_name("Failed step")
    assert step_lvl2_first.indent == step_lvl2_second.indent

    assert steps_section.indent < step_lvl1_first.indent < step_lvl2_first.indent
    step_lvl1_second.click() # restore sections state


def check_text_coloring(page_style, steps_section):
    check_styles(page_style)
    check_elements_classes(steps_section)


def check_styles(page_style):
    check_body_style(page_style)
    check_css_class(page_style, name="sectionTitle", exp_color="darkslateblue", exp_font="bold")
    check_css_class(page_style, name="sectionSuccessStatus", exp_color="green", exp_font="bold")
    check_css_class(page_style, name="sectionFailedStatus", exp_color="red", exp_font="bold")


def check_elements_classes(steps_section):
    steps_body = steps_section.get_section_body()

    check_section_elements_classes(steps_body.get_section_by_name("Success step"))
    check_section_elements_classes(steps_body.get_section_by_name("Failed step"), is_failed=True)
    check_section_elements_classes(steps_body.get_section_by_name("Partially success step"))

    composite_step = steps_body.get_section_by_name("Partially success step")
    composite_step.click()
    composite_step_body = composite_step.get_section_body()

    check_section_elements_classes(composite_step_body.get_section_by_name("Success step"))
    check_section_elements_classes(composite_step_body.get_section_by_name("Failed step"), is_failed=True)

    composite_step.click()  # restore sections state


def check_step_collapsed(section, body):
    assert section.is_section_collapsed
    assert body.is_body_collapsed
    assert not body.is_displayed()


def check_step_not_collapsed(section, body):
    assert not section.is_section_collapsed
    assert not body.is_body_collapsed
    assert body.is_displayed()


def check_section_elements_classes(step, is_failed=False):
    assert step.get_section_title_class() == "sectionTitle"
    step.click() # open section body
    exp_status = "Failed" if is_failed else "Success"
    assert step.get_section_status_class() == f"section{exp_status}Status"
    step.click() # close section body


def check_body_style(style):
    body_style = parse_css_block(style, "body")
    assert parse_css_property(body_style, "background-color") == "white"
    assert parse_css_property(body_style, "color") == "black"


def check_css_class(style, name, exp_color, exp_font):
    class_style = parse_css_block(style, f".{name}")
    assert parse_css_property(class_style, "color") == exp_color
    assert parse_css_property(class_style, "font-weight") == exp_font


def parse_css_block(style, block_name):
    return re.search(block_name + r" \{(.*?)\}", style, re.DOTALL).group(1)


def parse_css_property(style, css_property):
    return re.search(fr"\s{css_property}: (\w+)", style).group(1)


def get_page_style(browser):
    head = browser.find_element_by_tag_name("head")
    assert head
    style = head.find_element_by_tag_name("style")
    assert style
    return style.get_attribute("innerHTML")


class TestElement(FirefoxWebElement):

    __test__ = False # disable pytest collection for this class

    @staticmethod
    def create(element):
        assert element
        element.__class__ = TestElement
        return element

    # <any_tag>  <-- self
    #     <input type="checkbox" id="1." class="hide">
    #     <label for="1.">  <-- returning this element
    #         <span class="sectionLbl">1. Section name</span>  <-- Searching for this element
    #     </label>
    #     <div>Section body</div>
    # </any_tag>
    def get_section_by_name(self, section_name):
        span_elements = self.find_elements_by_class_name("sectionLbl")
        result = None
        for el in span_elements:
            if section_name in el.text:
                result = el.find_element_by_xpath("..")
        return TestElement.create(result)

    # <input type="checkbox" id="1." class="hide">
    # <label for="1.">  <-- self
    #     <span class="sectionLbl">1. Section name</span>
    # </label>
    # <div>Section body</div>  <-- returning this element
    def get_section_body(self):
        body = TestElement.create(self.find_element_by_xpath("./following-sibling::*[1]"))
        assert body.tag_name == "div"
        return body

    # <label for="1.">  <-- self
    #     <span class="sectionLbl">
    #         <span class="sectionTitle">1. Section name</span>  <-- returning this element class name
    #     </span>
    # </label>
    def get_section_title_class(self):
        label_span = self.find_element_by_class_name("sectionLbl")
        assert label_span
        title_span = label_span.find_element_by_tag_name("span")
        assert title_span
        return title_span.get_attribute("class")

    # <label for="1.">  <-- self
    #     ...
    # </label>
    # <div>
    #     ...
    #     <span class="sectionSuccessStatus">[Success]</span>  <-- returning this element class name
    # </div>
    def get_section_status_class(self):
        body = self.get_section_body()
        status_element = TestElement.create(body.find_elements_by_tag_name("span")[-1])
        assert status_element.text in ("[Success]", "[Failed]")
        return status_element.get_attribute("class")

    @property
    def is_body_collapsed(self):
        display_state = self.value_of_css_property("display")
        collapsed_state = "none"
        not_collapsed_state = "block"
        if display_state not in (collapsed_state, not_collapsed_state):
            raise RuntimeError(f"Unexpected element display state: '{display_state}'")

        collapsed = (display_state == collapsed_state)
        collapsed &= (not self.text)
        return collapsed

    @property
    def is_section_collapsed(self):
        label_span = self.find_element_by_tag_name("span")
        assert label_span
        script = "return window.getComputedStyle(arguments[0],':before').getPropertyValue('content')"
        section_state = self.parent.execute_script(script, label_span).replace('"', "").replace(" ", "")
        collapsed_state = "[+]"
        not_collapsed_state = "[-]"
        if section_state not in (collapsed_state, not_collapsed_state):
            raise RuntimeError(f"Unexpected section collapsed state: '{section_state}'")

        return section_state == collapsed_state

    @property
    def indent(self):
        return self.location['x']
