from typing import Union, List
import pytest

from universum import __main__
from universum.lib.module_arguments import IncorrectParameterError
from . import utils


def get_match_all(*args):
    """
    :param args: each argument is a pattern to be found in the error text
    :return: regular expression pattern that matches the string only if each argument pattern is found

    Example:

    >>> get_match_all("a", "b")
    '(?is)(?=.*a)(?=.*b)'
    """

    # (?is) means "ignore case" and "dot matches newline character"
    return "(?is)" + "".join(f"(?=.*{arg})" for arg in args)


def create_settings(test_type, vcs_type):
    settings = utils.create_empty_settings(test_type)
    settings.Output.type = "term"
    if test_type == "github-handler":
        settings.GithubHandler.event = "event"
        settings.GithubHandler.payload = "{}"
        settings.GithubHandler.trigger_url = "http://example.com"
        settings.GithubToken.integration_id = "1234"
        settings.GithubToken.key = "/path"
        return settings

    settings.ProjectDirectory.project_root = "project_root"
    settings.Vcs.type = vcs_type

    if test_type == "poll":
        settings.Poll.db_file = "p4poll.json"
    elif test_type == "submit":
        settings.Submit.commit_message = "Test CL"
    elif test_type == "main":
        settings.Launcher.config_path = "../configs.py"
        settings.ArtifactCollector.artifact_dir = "artifacts"

        settings.AutomationServer.type = "tc"
        settings.TeamcityServer.server_url = "https://teamcity"
        settings.TeamcityServer.build_id = "BuildId_167"
        settings.TeamcityServer.configuration_id = "TestConfig"
        settings.TeamcityServer.user_id = "TeamCityUser"
        settings.TeamcityServer.passwd = "TeamCityPassword"

    if vcs_type in ["git", "gerrit", "github"]:
        settings.GitVcs.repo = "ssh://user@127.0.0.1"
        # the refspec is crafted to satisfy requirements of our gerrit module, and others don't care
        settings.GitVcs.refspec = "refs/changes/00/000000/0"
        if test_type == "submit":
            settings.GitSubmitVcs.user = "Testing User"
            settings.GitSubmitVcs.email = "some@email.com"
        elif test_type == "main" and vcs_type == "github":
            settings.GitMainVcs.checkout_id = "HEAD"
            settings.GithubMainVcs.check_id = "000000000"
            settings.GithubToken.integration_id = "1234"
            settings.GithubToken.key = "/path"
            settings.GithubTokenWithInstallation.installation_id = "5678"
    elif vcs_type == "none":
        if test_type == "main":
            settings.LocalMainVcs.source_dir = "temp"
    elif vcs_type == "p4":
        settings.PerforceVcs.port = "127.0.0.1:1666"
        settings.PerforceVcs.user = "p4user"
        settings.PerforceVcs.password = "p4password"

        if test_type == "main":
            settings.PerforceMainVcs.client = "p4_disposable_workspace"
            settings.PerforceMainVcs.force_clean = True
            settings.MainVcs.report_to_review = True
            settings.Swarm.review_id = "123"
            settings.Swarm.change = "456"
            settings.Swarm.server_url = "https://swarm"

        if test_type in ("main", "poll",):
            settings.PerforceWithMappings.project_depot_path = "//depot"

        if test_type == "submit":
            settings.PerforceSubmitVcs.client = "p4_client"

    return settings


def parametrize_unset(parameter_name="unset"):
    return pytest.mark.parametrize(parameter_name, [
        lambda x, y, z: delattr(getattr(x, y), z),
        lambda x, y, z: setattr(getattr(x, y), z, None),
        lambda x, y, z: setattr(getattr(x, y), z, "")
    ], ids=["del", "none", "empty"])


def assert_incorrect_parameter(settings, match):
    with pytest.raises(IncorrectParameterError, match=match):
        __main__.run(settings)


missing_params = []


def param(test_type: str, module: str, field: str,
          vcs_type: Union[str, List[str]] = "*", error_match: str = None) -> None:
    global missing_params

    if isinstance(vcs_type, list):
        for specific_vcs_type in vcs_type:
            param(test_type, module, field, specific_vcs_type, error_match)
        return

    if vcs_type == "*":
        param(test_type, module, field, ["p4", "git", "gerrit", "github", "none"], error_match)
        return

    if test_type == "*":
        for specific_test_type in ["main", "submit", "poll"]:
            param(specific_test_type, module, field, vcs_type, error_match)
        return

    if error_match is None:
        error_match = field

    test_id = test_type + "-" + vcs_type + "-" + module + "." + field
    missing_params.append(pytest.param(test_type, module, field, vcs_type, error_match, id=test_id))


param("main",           "Launcher",                     "config_path")
param("submit",         "Submit",                       "commit_message",  vcs_type=["p4", "git", "gerrit", "github"])
param("submit",         "PerforceSubmitVcs",            "client",          vcs_type="p4")
param("main",           "PerforceMainVcs",              "client",          vcs_type="p4")
param("main",           "LocalMainVcs",                 "source_dir",      vcs_type="none")
param("submit",         "GitSubmitVcs",                 "user",            vcs_type=["git", "gerrit", "github"])
param("submit",         "GitSubmitVcs",                 "email",           vcs_type=["git", "gerrit", "github"])
param("main",           "TeamcityServer",               "build_id")
param("main",           "TeamcityServer",               "configuration_id")
param("main",           "TeamcityServer",               "server_url",      error_match="TEAMCITY_SERVER")
param("main",           "TeamcityServer",               "user_id",         error_match="TC_USER")
param("main",           "TeamcityServer",               "passwd",          error_match="TC_PASSWD")
param("*",              "PerforceVcs",                  "port",            vcs_type="p4", error_match="perforce port")
param("*",              "PerforceVcs",                  "user",            vcs_type="p4")
param("*",              "PerforceVcs",                  "password",        vcs_type="p4")
param("main",           "Swarm",                        "server_url",      vcs_type="p4", error_match="SWARM_SERVER")
param("main",           "Swarm",                        "review_id",       vcs_type="p4", error_match="review number")
param("main",           "Swarm",                        "change",          vcs_type="p4")
param("*",              "Vcs",                          "type")
param("*",              "GitVcs",                       "repo",            vcs_type=["git", "gerrit", "github"],
      error_match="git repo")
param("main",           "GitVcs",                       "refspec",         vcs_type="gerrit")
param("main",           "GitMainVcs",                   "checkout_id",     vcs_type="github")
param("main",           "GithubMainVcs",                "check_id",        vcs_type="github")
param("main",           "GithubToken",                  "integration_id",  vcs_type="github",
      error_match="GITHUB_APP_ID")
param("github-handler", "GithubToken",                  "integration_id",  error_match="GITHUB_APP_ID")
param("main",           "GithubToken",                  "key",             vcs_type="github")
param("github-handler", "GithubToken",                  "key")
param("github-handler", "GithubHandler",                "event",           error_match="GITHUB_EVENT")
param("github-handler", "GithubHandler",                "payload",         error_match="GITHUB_PAYLOAD")
param("github-handler", "GithubHandler",                "trigger_url")
param("main",           "GithubTokenWithInstallation",  "installation_id", vcs_type="github",
      error_match="GITHUB_INSTALLATION_ID")


@parametrize_unset()
@pytest.mark.parametrize("test_type, module, field, vcs_type, error_match", missing_params)
def test_missing_params(unset, test_type, module, field, vcs_type, error_match):
    """
    Make sure the exact error message is produced for the empty settings field
    """
    settings = create_settings(test_type, vcs_type)
    unset(settings, module, field)

    assert_incorrect_parameter(settings, "(?i)" + error_match)


@pytest.mark.parametrize("test_type, module, field, vcs_type, error_match", missing_params)
def test_missing_params_correct_error(test_type, module, field, vcs_type, error_match):
    """
    Make sure the error message is not produced if the settings field is not empty
    """
    settings = create_settings(test_type, vcs_type)

    # remove some other setting and make sure there is no error message for current one
    if test_type == "main":
        if module == "Launcher" and field == "config_path":
            settings.Vcs.type = ""
        else:
            settings.Launcher.config_path = ""
    elif test_type == "submit":
        if module == "Submit" and field == "commit_message":
            settings.Vcs.type = ""
        else:
            settings.Submit.commit_message = ""
    elif test_type == "poll":
        settings.AutomationServer.type = "jenkins"
        settings.JenkinsServerForTrigger.trigger_url = ""
    elif test_type == "github-handler":
        if module == "GithubToken" and field == "integration_id":
            settings.GithubToken.key = ""
        else:
            settings.GithubToken.integration_id = ""

    # the regular expression verifies that the string is not located in the error text
    with pytest.raises(IncorrectParameterError, match=f"(?is)^((?!{error_match}).)*$"):
        __main__.run(settings)


@parametrize_unset("unset_mappings")
@parametrize_unset("unset_depot_path")
def test_missing_both_perforce_mappings_and_depot_path(unset_mappings, unset_depot_path):
    settings = create_settings("main", "p4")
    unset_mappings(settings, "PerforceWithMappings", "mappings")
    unset_depot_path(settings, "PerforceWithMappings", "project_depot_path")

    assert_incorrect_parameter(settings, mappings_error_match)


def test_present_both_perforce_mappings_and_depot_path():
    settings = create_settings("main", "p4")
    settings.PerforceWithMappings.mappings = ["//depot/... /..."]

    assert_incorrect_parameter(settings, mappings_error_match)


@parametrize_unset()
@pytest.mark.parametrize("vcs_type", ["p4", "git", "gerrit"])
def test_missing_jenkins_params(unset, vcs_type):
    settings = create_settings("main", vcs_type)
    settings.AutomationServer.type = "jenkins"
    unset(settings, "JenkinsServerForHostingBuild", "build_url")

    assert_incorrect_parameter(settings, "build-url")

    settings = create_settings("poll", vcs_type)
    settings.AutomationServer.type = "jenkins"
    unset(settings, "JenkinsServerForTrigger", "trigger_url")

    assert_incorrect_parameter(settings, "trigger-url")

    settings = create_settings("poll", vcs_type)
    settings.AutomationServer.type = "tc"
    settings.TeamcityServer.server_url = ""

    # the regular expression verifies that the string is not located in the error text
    with pytest.raises(IncorrectParameterError, match=f"(?is)^((?!Jenkins url for triggering build).)*$"):
        __main__.run(settings)


@pytest.mark.parametrize("vcs_type", ["git", "none"])
def test_code_review_for_unsupported_vcs(vcs_type):
    settings = create_settings("main", vcs_type)
    settings.MainVcs.report_to_review = True

    assert_incorrect_parameter(settings, "code review system")


def test_gerrit_non_ssh_repo():
    settings = create_settings("main", "gerrit")
    settings.GitVcs.repo = "https://gerrit"

    assert_incorrect_parameter(settings, "ssh protocol")


def test_gerrit_wrong_refspec():
    settings = create_settings("main", "gerrit")
    settings.GitVcs.refspec = "no slashes in this string"

    assert_incorrect_parameter(settings, "incorrect format")


def test_gerrit_no_username_in_ssh_repo():
    settings = create_settings("main", "gerrit")
    settings.GitVcs.repo = "ssh://127.0.0.1"

    assert_incorrect_parameter(settings, "user name")


def test_swarm_changelist_incorrect_format():
    settings = create_settings("main", "p4")
    settings.Swarm.change = "123,456"

    assert_incorrect_parameter(settings, "changelist for unshelving is incorrect")


def test_vcs_type_and_config_path():
    settings = create_settings("main", "p4")
    settings.Launcher.config_path = None
    settings.Vcs.type = None

    assert_incorrect_parameter(settings, get_match_all("CONFIG_PATH", "repository type"))


def test_source_dir_and_config_path():
    settings = create_settings("main", "p4")
    settings.Vcs.type = "none"
    settings.Launcher.config_path = None
    settings.LocalMainVcs.source_dir = None

    assert_incorrect_parameter(settings, get_match_all("CONFIG_PATH", "SOURCE_DIR"))
