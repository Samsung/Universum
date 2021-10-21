# pylint: disable = redefined-outer-name

import os
import re
import pytest

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webelement import FirefoxWebElement

from universum import __main__
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
    env = utils.TestEnvironment(tmpdir, test_type)
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
    assert not __main__.run(environment_main_and_nonci.settings)
    check_html_log(environment_main_and_nonci.artifact_dir, browser)


def test_success_clean_build(tmpdir, browser):
    env = create_environment("main", tmpdir)
    env.settings.Main.clean_build = True
    assert not __main__.run(env.settings)
    check_html_log(env.artifact_dir, browser)


def test_no_html_log_requested(environment_main_and_nonci):
    environment_main_and_nonci.settings.Output.html_log = False
    assert not __main__.run(environment_main_and_nonci.settings)
    log_path = os.path.join(environment_main_and_nonci.artifact_dir, "log.html")
    assert not os.path.exists(log_path)


def check_html_log(artifact_dir, browser):
    log_path = os.path.join(artifact_dir, "log.html")
    assert os.path.exists(log_path)

    browser.get(f"file://{log_path}")
    html_body = TestElement.create(browser.find_element_by_tag_name("body"))
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
    check_coloring(html_body, steps_section)
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


def check_coloring(body_element, steps_section):
    check_body_coloring(body_element)
    check_text_coloring(steps_section)


def check_body_coloring(body_element):
    black_rgb = "rgb(0, 0, 0)"
    assert body_element.color == black_rgb
    white_rgb = "rgb(255, 255, 255)"
    assert body_element.background_color == white_rgb


def check_text_coloring(steps_section):
    steps_body = steps_section.get_section_body()

    check_section_coloring(steps_body.get_section_by_name("Success step"))
    check_section_coloring(steps_body.get_section_by_name("Failed step"), is_failed=True)
    check_section_coloring(steps_body.get_section_by_name("Partially success step"))

    composite_step = steps_body.get_section_by_name("Partially success step")
    composite_step.click()
    composite_step_body = composite_step.get_section_body()

    check_section_coloring(composite_step_body.get_section_by_name("Success step"))
    check_section_coloring(composite_step_body.get_section_by_name("Failed step"), is_failed=True)

    composite_step.click() # restore sections state


def check_step_collapsed(section, body):
    assert section.is_section_collapsed
    assert body.is_body_collapsed
    assert not body.is_displayed()


def check_step_not_collapsed(section, body):
    assert not section.is_section_collapsed
    assert not body.is_body_collapsed
    assert body.is_displayed()


def check_section_coloring(step, is_failed=False):
    check_title_coloring(step.get_section_title())
    step.click() # open section body
    check_status_coloring(step.get_section_status(), is_failed)
    step.click() # close section body


def check_title_coloring(title):
    blue_rgb = "rgb(72, 61, 139)"
    assert title.color == blue_rgb
    check_text_is_bold(title)


def check_status_coloring(status, is_failed):
    green_rgb = "rgb(0, 128, 0)"
    red_rgb = "rgb(255, 0, 0)"
    exp_color = red_rgb if is_failed else green_rgb
    assert status.color == exp_color
    check_text_is_bold(status)


def check_text_is_bold(element):
    font_weight_bold = "700"
    assert element.font_weight == font_weight_bold



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
    #         <span class="sectionTitle">1. Section name</span>  <-- returning this element
    #     </span>
    # </label>
    def get_section_title(self):
        label_span = self.find_element_by_class_name("sectionLbl")
        assert label_span
        title_span = label_span.find_element_by_tag_name("span")
        return TestElement.create(title_span)

    # <label for="1.">  <-- self
    #     ...
    # </label>
    # <div>
    #     ...
    #     <span class="sectionSuccessStatus">[Success]</span>  <-- returning this element
    # </div>
    def get_section_status(self):
        body = self.get_section_body()
        status_element = TestElement.create(body.find_elements_by_tag_name("span")[-1])
        assert status_element.text in ("[Success]", "[Failed]")
        return TestElement.create(status_element)

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

    @property
    def color(self):
        return self.value_of_css_property("color")

    @property
    def font_weight(self):
        return self.value_of_css_property("font-weight")

    @property
    def background_color(self):
        return self.value_of_css_property("background-color")
