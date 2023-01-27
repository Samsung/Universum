# pylint: disable = redefined-outer-name

import os
import re
from datetime import datetime
from enum import Enum, auto
import colorsys
import pytest

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webelement import FirefoxWebElement

from universum import __main__
from . import utils


config = r"""
from universum.configuration_support import Configuration

failed_step_cmd = ["bash", "-c", '1>&2 echo "error"; exit 1']

success_links_step = Configuration([dict(name="Success links step",
    command=["echo", "http://www.samsung.com/ https://www.samsung.com/ ftp://www.samsung.com " +
        r"file://www.samsung.com/remote_file file:///local\ file mailto:asdf@samsung.com"])])
success_ansi_step = Configuration([dict(name="Success ansi step",
    command=["echo", "\u001b[31m red \u001b[0m, \u001b[42m\u001b[34m blue on green \u001b[0m, " +
        "\u001b[1m\u001b[4m\u001b[36m bold underline cyan \u001b[0m"])])
failed_step = Configuration([dict(name="Failed step", command=failed_step_cmd)])
partially_success_step = Configuration([dict(name="Partially success step: ")])
all_success_step = Configuration([dict(name="All success step: ")])
all_failed_step = Configuration([dict(name="All failed step: ")])
failed_critical_step = Configuration([dict(name="Failed step", command=failed_step_cmd, critical=True)])

configs = \
    success_links_step + \
    success_ansi_step + \
    failed_step + \
    partially_success_step * (success_links_step + failed_step) + \
    all_success_step * (success_links_step + success_ansi_step) + \
    all_failed_step * (failed_step + failed_step) + \
    failed_critical_step + success_links_step
"""

log_name = "universum_log"


def create_environment(test_type, tmp_path):
    env = utils.LocalTestEnvironment(tmp_path, test_type)
    env.configs_file.write_text(config)
    env.settings.Output.html_log = log_name
    return env


@pytest.fixture(params=["main", "nonci"])
def environment_main_and_nonci(request, tmp_path):
    yield create_environment(request.param, tmp_path)


@pytest.fixture()
def browser():
    options = Options()
    options.headless = True
    firefox = webdriver.Firefox(options=options)
    yield firefox
    firefox.close()


def test_cli_log_custom_name(tmp_path):
    custom_log_name = "custom_name.html"
    artifact_dir = check_cli(tmp_path, ["-hl", custom_log_name])
    assert os.path.exists(os.path.join(artifact_dir, custom_log_name))


def test_cli_log_default_name(tmp_path):
    artifact_dir = check_cli(tmp_path, ["-hl"])
    assert os.path.exists(os.path.join(artifact_dir, "universum_log.html"))


def test_cli_no_log_requested(tmp_path):
    artifact_dir = check_cli(tmp_path, [])
    for file_name in os.listdir(artifact_dir):
        assert not file_name.endswith(".html")


def test_success(environment_main_and_nonci, browser):
    environment_main_and_nonci.run()
    check_html_log(environment_main_and_nonci.artifact_dir, browser)


def test_success_clean_build(tmp_path, browser):
    env = create_environment("main", tmp_path)
    env.settings.Main.clean_build = True
    env.run()
    check_html_log(env.artifact_dir, browser)


def check_html_log(artifact_dir, browser):
    log_path = os.path.join(artifact_dir, log_name)
    assert os.path.exists(log_path)

    browser.get(f"file://{log_path}")
    html_body = TestElement.create(browser.find_element_by_tag_name("body"))
    body_elements = html_body.find_elements_by_xpath("./pre")
    assert len(body_elements) == 1

    universum_log_element = TestElement.create(body_elements[0])
    steps_section = universum_log_element.get_section_by_name("Executing build steps")
    steps_body = steps_section.get_section_body()

    check_initial_sections_display_state(universum_log_element, steps_body)
    check_manual_section_expanding(steps_body)
    check_sections_indentation(steps_section)
    check_coloring(html_body, universum_log_element, steps_body)
    check_links_wrapping(steps_body)
    check_ansi_colors_convertion(steps_body)
    check_dark_mode(html_body, universum_log_element)
    check_timestamps(html_body, universum_log_element)


def check_initial_sections_display_state(universum_log_element, steps_body):
    assert steps_body.is_displayed()
    sections_expanded_state = {
        "Success links step": False,
        "Failed step": True,
        "Partially success step": True,
        "Partially success step: Success links step": False,
        "Partially success step: Failed step": True,
        "All success step": False,
        "All failed step": True,
        "All failed step: Failed step": True
    }
    for section_name, expanded_state in sections_expanded_state.items():
        assert steps_body.get_section_body_by_name(section_name).is_displayed() == expanded_state
    assert universum_log_element.get_section_body_by_name("Reporting build result").is_displayed()


def check_manual_section_expanding(steps_body):
    success_step = steps_body.get_section_by_name("Success links step")
    success_step_body = success_step.get_section_body()
    assert not success_step_body.is_displayed()
    success_step.click()
    assert success_step_body.is_displayed()
    success_step.click()
    assert not success_step_body.is_displayed()


def check_sections_indentation(steps_section):
    steps_body = steps_section.get_section_body()
    step_lvl1_first = steps_body.get_section_by_name("Failed step")
    step_lvl1_second = steps_body.get_section_by_name("Partially success step")
    assert step_lvl1_first.indent == step_lvl1_second.indent

    step_lvl1_body = step_lvl1_second.get_section_body()
    step_lvl2_first = step_lvl1_body.get_section_by_name("Success links step")
    step_lvl2_second = step_lvl1_body.get_section_by_name("Failed step")
    assert step_lvl2_first.indent == step_lvl2_second.indent

    assert steps_section.indent < step_lvl1_first.indent < step_lvl2_first.indent


def check_coloring(body_element, universum_log_element, steps_body):
    check_body_coloring(body_element)
    check_title_and_status_coloring(steps_body)
    check_skipped_steps_coloring(steps_body)
    check_steps_report_coloring(universum_log_element)
    check_errors_tags_coloring(steps_body)


def check_body_coloring(body_element):
    assert body_element.color == Color.BLACK
    assert body_element.background_color == Color.WHITE


def check_title_and_status_coloring(steps_body):
    check_section_coloring(steps_body.get_section_by_name("Success links step"))
    check_section_coloring(steps_body.get_section_by_name("Failed step"), is_failed=True)
    check_section_coloring(steps_body.get_section_by_name("Partially success step"), is_failed=True)

    composite_step_body = steps_body.get_section_body_by_name("Partially success step")
    check_section_coloring(composite_step_body.get_section_by_name("Success links step"))
    check_section_coloring(composite_step_body.get_section_by_name("Failed step"), is_failed=True)


def check_skipped_steps_coloring(steps_body):
    skipped_steps = steps_body.find_elements_by_class_name("skipped")
    assert skipped_steps
    skipped_steps = [TestElement.create(step) for step in skipped_steps]
    for step in skipped_steps:
        assert step.color == Color.CYAN


def check_steps_report_coloring(universum_log_element):
    report_section_body = universum_log_element.get_section_body_by_name("Reporting build result")
    xpath_selector = "./*[text() = 'Success' or text() = 'Failed' or text() = 'Skipped']"
    elements = [TestElement.create(el) for el in report_section_body.find_elements_by_xpath(xpath_selector)]
    assert elements
    for el in elements:
        if el.text == "Success":
            assert el.color == Color.GREEN
        elif el.text in ("Failed", "Skipped"):
            assert el.color == Color.RED
        else:
            assert False, f"Unexpected element text: '{el.text}'"


def check_errors_tags_coloring(steps_body):
    step_body = steps_body.get_section_body_by_name("Failed step")
    exception_tag = step_body.get_child_by_text("Error:")
    assert exception_tag.color == Color.RED
    stderr_tag = step_body.get_child_by_text("stderr:")
    assert stderr_tag.color == Color.YELLOW


def check_section_coloring(step, is_failed=False):
    check_text_item_style(step.get_section_title(), is_failed, normal_color=Color.BLUE)
    if not is_failed:
        step.click()  # open section body
    check_text_item_style(step.get_section_status(), is_failed, normal_color=Color.GREEN)
    if not is_failed:
        step.click()  # close section body


def check_text_item_style(item, is_failed, normal_color):
    exp_color = Color.RED if is_failed else normal_color
    assert item.color == exp_color
    check_text_is_bold(item)


def check_text_is_bold(element):
    font_weight_bold = "700"
    assert element.font_weight == font_weight_bold


def check_links_wrapping(steps_body):
    step = steps_body.get_section_by_name("Success links step")
    body = step.get_section_body()
    assert not body.is_displayed()
    step.click()
    for url_scheme in ("http", "https", "ftp", "mailto"):
        assert body.find_element_by_partial_link_text(url_scheme)
    file_links = body.find_elements_by_partial_link_text("file")
    assert len(file_links) == 4 # `echo` parameters also counts
    link_with_whitespace = file_links[1]
    assert r"\ " in link_with_whitespace.text
    assert "%20" in link_with_whitespace.get_attribute("href")
    step.click() # restore section closed state


def check_ansi_colors_convertion(steps_body):
    step = steps_body.get_section_by_name("Success ansi step")
    body = step.get_section_body()
    assert not body.is_displayed()
    step.click()

    span_elements = body.find_elements_by_tag_name("span")
    def is_target_span_element(element):
        return element.text and element.get_attribute("style")
    span_elements = [TestElement.create(el) for el in span_elements if is_target_span_element(el)]
    assert len(span_elements) == 6 # 3 printed elements + 3 `echo` argument elements

    for element in span_elements:
        if "red" in element.text:
            assert element.color == Color.RED
        elif "blue on green" in element.text:
            assert element.color == Color.BLUE
            assert element.background_color == Color.GREEN
        elif "bold underline cyan" in element.text:
            check_text_is_bold(element)
            assert "underline" in element.value_of_css_property("text-decoration")
            assert element.color == Color.CYAN
        else:
            assert False, f"Unexpected span text: {element.text}"

    step.click() # restore section closed state


def check_dark_mode(body_element, universum_log_element):
    dark_mode_switch = TestElement.create(body_element.find_element_by_xpath("./label[@for='dark-checkbox']"))
    dark_mode_switch.click()
    assert universum_log_element.color == Color.WHITE
    assert universum_log_element.background_color == Color.BLACK
    dark_mode_switch.click()
    assert universum_log_element.color == Color.BLACK


def check_timestamps(body_element, universum_log_element):
    timestamp_element = universum_log_element.find_element_by_xpath("./*[@class='time']")
    assert not timestamp_element.is_displayed()

    time_switch = TestElement.create(body_element.find_element_by_xpath("./label[@for='time-checkbox']"))
    time_switch.click()
    assert timestamp_element.is_displayed()

    timestamp = datetime.strptime(timestamp_element.text, "%Y-%m-%d %H:%M:%S")
    delta = abs(datetime.now() - timestamp)
    assert delta.days == 0
    assert delta.seconds <= 60


def check_cli(tmp_path, html_log_params):
    artifact_dir = tmp_path / "artifacts"
    config_file = tmp_path / "configs.py"
    config_file.write_text(config, "utf-8")

    cli_params = ["-vt", "none",
                  "-fsd", str(tmp_path),
                  "-cfg", str(config_file),
                  "-ad", str(artifact_dir)]
    html_log_params.extend(cli_params)
    result = __main__.main(html_log_params)

    assert result == 0
    return artifact_dir


class TestElement(FirefoxWebElement):

    __test__ = False # disable pytest collection for this class

    @staticmethod
    def create(element):
        assert element
        element.__class__ = TestElement
        return element

    def get_section_body_by_name(self, section_name):
        return self.get_section_by_name(section_name).get_section_body()

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
                return TestElement.create(el.find_element_by_xpath(".."))
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
        xpath_selector = "./*[contains(text(), '[Success]') or contains(text(), '[Failed]')]"
        return TestElement.create(body.find_elements_by_xpath(xpath_selector)[-1])

    def get_child_by_text(self, text):
        xpath_selector = f"./*[text() = '{text}']"
        return TestElement.create(self.find_element_by_xpath(xpath_selector))

    @property
    def indent(self):
        return self.location['x']

    @property
    def color(self):
        return self._get_primary_color(self.value_of_css_property("color"))

    @property
    def background_color(self):
        return self._get_primary_color(self.value_of_css_property("background-color"))

    @property
    def font_weight(self):
        return self.value_of_css_property("font-weight")

    @staticmethod
    def _get_primary_color(rgb_str):
        re_result = re.match(r"^rgb\((\d{1,3}), (\d{1,3}), (\d{1,3})\)$", rgb_str)
        assert re_result
        red, green, blue = int(re_result.group(1)), int(re_result.group(2)), int(re_result.group(3))
        hue, lightness, _ = colorsys.rgb_to_hls(red/255.0, green/255.0, blue/255.0)
        hue = 360 * hue
        lightness = 100 * lightness

        color = None
        if lightness <= 20:
            color = Color.BLACK
        elif lightness >= 80:
            color = Color.WHITE
        elif 0 <= hue <= 30 or 330 <= hue <= 360:
            color = Color.RED
        elif 30 <= hue <= 80:
            color = Color.YELLOW
        elif 80 <= hue <= 150:
            color = Color.GREEN
        elif 150 <= hue <= 190:
            color = Color.CYAN
        elif 190 <= hue <= 270:
            color = Color.BLUE
        elif 270 <= hue <= 330:
            color = Color.PURPLE
        else:
            assert False, "Should not occur"
        return color


class Color(Enum):
    BLACK = auto()
    WHITE = auto()
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    YELLOW = auto()
    PURPLE = auto()
    CYAN = auto()
