from typing import Union, List, Optional
import pytest

from universum import __main__
from universum.lib.module_arguments import IncorrectParameterError, ModuleNamespace
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


def create_settings(test_type: str, vcs_type: str) -> ModuleNamespace:
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
        settings.AutomationServer.type = "tc"
        settings.TeamcityServer.server_url = "https://teamcity"
        settings.TeamcityServer.build_id = "BuildId_167"
        settings.TeamcityServer.configuration_id = "TestConfig"
        settings.TeamcityServer.user_id = "TeamCityUser"
        settings.TeamcityServer.passwd = "TeamCityPassword"

    if vcs_type in ["git", "gerrit", "ghapp", "ghactions"]:
        if test_type == "main" and vcs_type == "ghactions":
            settings.GithubActionsMainVcs.token = "token"
            settings.GithubActionsMainVcs.payload = "{\"repository\": {\"html_url\": \"None\"}," \
                                                    " \"pull_request\": {\"head\": {\"ref\": \"None\"}}}"
        else:
            settings.GitVcs.repo = "ssh://user@127.0.0.1"
            # the refspec is crafted to satisfy requirements of our gerrit module, and others don't care
            settings.GitVcs.refspec = "refs/changes/00/000000/0"
        if test_type == "submit":
            settings.GitSubmitVcs.user = "Testing User"
            settings.GitSubmitVcs.email = "some@email.com"
        elif test_type == "main" and vcs_type == "ghapp":
            settings.GitMainVcs.checkout_id = "HEAD"
            settings.GithubAppMainVcs.check_id = "000000000"
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
        lambda x, y, z: setattr(getattr(x, y), z, None),
        lambda x, y, z: setattr(getattr(x, y), z, "")
    ], ids=["none", "empty"])


def assert_incorrect_parameter(settings: ModuleNamespace, *args):
    with pytest.raises(IncorrectParameterError, match=get_match_all(*args)):
        __main__.run(settings)


missing_params = []


def param(test_type: str, module: str, field: str,
          vcs_type: Union[str, List[str]] = "*", error_match: Optional[str] = None) -> None:

    if isinstance(vcs_type, list):
        for specific_vcs_type in vcs_type:
            param(test_type, module, field, specific_vcs_type, error_match)
        return

    if vcs_type == "*":
        param(test_type, module, field, ["p4", "git", "gerrit", "ghapp", "ghactions", "none"], error_match)
        return

    if test_type == "*":
        for specific_test_type in ["main", "submit", "poll"]:
            param(specific_test_type, module, field, vcs_type, error_match)
        return

    if error_match is None:
        error_match = field

    test_id = test_type + "-" + vcs_type + "-" + module + "." + field
    missing_params.append(pytest.param(test_type, module, field, vcs_type, error_match, id=test_id))


param("submit",         "Submit",                       "commit_message",
      vcs_type=["p4", "git", "gerrit", "ghapp", "ghactions"])
param("submit",         "PerforceSubmitVcs",            "client",          vcs_type="p4")
param("main",           "PerforceMainVcs",              "client",          vcs_type="p4")
param("main",           "LocalMainVcs",                 "source_dir",      vcs_type="none")
param("submit",         "GitSubmitVcs",                 "user",
      vcs_type=["git", "gerrit", "ghapp", "ghactions"])
param("submit",         "GitSubmitVcs",                 "email",
      vcs_type=["git", "gerrit", "ghapp", "ghactions"])
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
param("*",              "GitVcs",                       "repo",            vcs_type=["git", "gerrit", "ghapp"],
      error_match="git repo")
param("main",           "GitVcs",                       "refspec",         vcs_type="gerrit")
param("main",           "GitMainVcs",                   "checkout_id",     vcs_type="ghapp")
param("main",           "GithubAppMainVcs",             "check_id",        vcs_type="ghapp")
param("main",           "GithubActionsMainVcs",         "token",           vcs_type="ghactions")
param("main",           "GithubActionsMainVcs",         "payload",         vcs_type="ghactions")
param("main",           "GithubToken",                  "integration_id",  vcs_type="ghapp",
      error_match="GITHUB_APP_ID")
param("github-handler", "GithubToken",                  "integration_id",  error_match="GITHUB_APP_ID")
param("main",           "GithubToken",                  "key",             vcs_type="ghapp")
param("github-handler", "GithubToken",                  "key")
param("github-handler", "GithubHandler",                "event",           error_match="GITHUB_EVENT")
param("github-handler", "GithubHandler",                "payload",         error_match="GITHUB_PAYLOAD")
param("github-handler", "GithubHandler",                "trigger_url")
param("main",           "GithubTokenWithInstallation",  "installation_id", vcs_type="ghapp",
      error_match="GITHUB_INSTALLATION_ID")


@parametrize_unset()
@pytest.mark.parametrize("test_type, module, field, vcs_type, error_match", missing_params)
def test_missing_params(unset, test_type, module, field, vcs_type, error_match):
    """
    Make sure the exact error message is produced for the empty settings field
    """
    settings = create_settings(test_type, vcs_type)
    unset(settings, module, field)

    assert_incorrect_parameter(settings, error_match)


@pytest.mark.parametrize("test_type, module, field, vcs_type, error_match", missing_params)
def test_missing_params_correct_error(test_type, module, field, vcs_type, error_match):
    """
    Make sure the error message is not produced if the settings field is not empty
    """
    settings = create_settings(test_type, vcs_type)

    # The idea of the test is to remove some other setting and make sure there is no error message for the current
    # one. For each test type (universum launch type), we choose some settings field to be set to the empty string.
    # At the same time we do not set the current settings field to the empty string. This should generate exception
    # with proper error message, which doesn't contain error regarding the current field passed in parameters.
    # However, this doesn't work if the chosen setting is equal to the one passed in parameters. In that case we use
    # some other setting.
    if test_type == "main":
        if module == "TeamcityServer" and field == "build_id":
            settings.TeamcityServer.configuration_id = ""
        else:
            settings.TeamcityServer.build_id = ""
    elif test_type == "submit":
        if module == "Submit" and field == "commit_message":
            settings.Vcs.type = ""
        else:
            settings.Submit.commit_message = ""
    elif test_type == "poll":
        # The jenkins trigger_url is the only common mandatory settings field of the 'poll' launch type.
        # However, this field is not added to the test parametrization list, so there is no need to set some other
        # field to the empty string to check trigger_url. This parameter is checked in separate test.
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


mappings_error_match = get_match_all("P4_PATH", "P4_MAPPINGS")


@parametrize_unset("unset_mappings")
@parametrize_unset("unset_depot_path")
def test_missing_both_perforce_mappings_and_depot_path(unset_mappings, unset_depot_path):
    settings = create_settings("main", "p4")
    unset_mappings(settings, "PerforceWithMappings", "mappings")
    unset_depot_path(settings, "PerforceWithMappings", "project_depot_path")

    assert_incorrect_parameter(settings, "P4_PATH", "P4_MAPPINGS")


def test_present_both_perforce_mappings_and_depot_path():
    settings = create_settings("main", "p4")
    settings.PerforceWithMappings.mappings = ["//depot/... /..."]

    assert_incorrect_parameter(settings, "P4_PATH", "P4_MAPPINGS")


@parametrize_unset()
@pytest.mark.parametrize("vcs_type", ["p4", "git", "gerrit"])
def test_missing_jenkins_params(unset, vcs_type):
    """
    Since varying the type of automation server seems like an overkill for the majority of argument checks,
    it is always set to "tc" (TeamCity). This test checks the correctness of checks for jeknins-specific settings.
    """
    settings = create_settings("main", vcs_type)
    settings.AutomationServer.type = "jenkins"
    unset(settings, "JenkinsServerForHostingBuild", "build_url")

    assert_incorrect_parameter(settings, "Jenkins url of the ongoing build")

    settings = create_settings("poll", vcs_type)
    settings.AutomationServer.type = "jenkins"
    unset(settings, "JenkinsServerForTrigger", "trigger_url")

    assert_incorrect_parameter(settings, "Jenkins url for triggering build")

    settings = create_settings("main", vcs_type)
    settings.AutomationServer.type = "tc"
    settings.TeamcityServer.server_url = ""

    # the regular expression verifies that the string is not located in the error text
    with pytest.raises(IncorrectParameterError, match="(?is)^((?!Jenkins url of the ongoing build).)*$"):
        __main__.run(settings)

    settings = create_settings("poll", vcs_type)
    settings.AutomationServer.type = "tc"
    settings.TeamcityServer.server_url = ""

    # the regular expression verifies that the string is not located in the error text
    with pytest.raises(IncorrectParameterError, match="(?is)^((?!Jenkins url for triggering build).)*$"):
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


def test_multiple_errors_main_vcs_type_and_build_id():
    settings = create_settings("main", "p4")
    settings.TeamcityServer.build_id = None
    settings.Vcs.type = None

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "repository type")


def test_multiple_errors_main_none_source_dir_and_build_id():
    settings = create_settings("main", "none")
    settings.TeamcityServer.build_id = None
    settings.LocalMainVcs.source_dir = None
    settings.MainVcs.report_to_review = True

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "SOURCE_DIR", "no code review system")


def test_multiple_errors_main_p4_params():
    settings = create_settings("main", "p4")

    settings.PerforceVcs.port = None
    settings.PerforceVcs.user = None
    settings.PerforceVcs.password = None
    settings.PerforceMainVcs.client = None
    settings.PerforceWithMappings.project_depot_path = None
    settings.Swarm.review_id = None
    settings.Swarm.change = None
    settings.Swarm.server_url = None
    settings.TeamcityServer.server_url = None
    settings.TeamcityServer.build_id = None
    settings.TeamcityServer.configuration_id = None
    settings.TeamcityServer.user_id = None
    settings.TeamcityServer.passwd = None

    assert_incorrect_parameter(settings, "port", "user name", "password", "mappings", "workspace",
                               "URL of the Swarm", "Swarm review number",
                               "Swarm changelist for unshelving is not specified", "URL of the TeamCity",
                               "id of the build on TeamCity", "id of the configuration on TeamCity",
                               "id of the TeamCity user", "password of the TeamCity user")

    settings = create_settings("main", "p4")

    settings.PerforceVcs.port = None
    settings.PerforceVcs.user = None
    settings.PerforceVcs.password = None
    settings.PerforceMainVcs.client = None
    settings.PerforceWithMappings.project_depot_path = None
    settings.Swarm.review_id = None
    settings.Swarm.change = "123,456"
    settings.Swarm.server_url = None

    assert_incorrect_parameter(settings, "port", "user name", "password", "mappings", "workspace",
                               "URL of the Swarm", "Swarm review number",
                               "Swarm changelist for unshelving is incorrect")

    settings = create_settings("main", "p4")

    settings.PerforceVcs.port = None
    settings.PerforceVcs.user = None
    settings.PerforceVcs.password = None
    settings.PerforceMainVcs.client = None
    settings.PerforceWithMappings.project_depot_path = None
    settings.AutomationServer.type = "jenkins"
    settings.JenkinsServerForHostingBuild.build_url = None

    assert_incorrect_parameter(settings, "port", "user name", "password", "mappings", "workspace",
                               "Jenkins url of the ongoing build")


def test_multiple_errors_submit_p4_params_and_commit_message():
    settings = create_settings("submit", "p4")
    settings.Submit.commit_message = None
    settings.PerforceVcs.port = None
    settings.PerforceVcs.user = None
    settings.PerforceVcs.password = None
    settings.PerforceSubmitVcs.client = None

    assert_incorrect_parameter(settings, "COMMIT_MESSAGE", "port", "user name", "password", "P4CLIENT")


def test_multiple_errors_main_git_params_and_build_id():
    settings = create_settings("main", "git")
    settings.TeamcityServer.build_id = None
    settings.GitVcs.repo = None
    settings.MainVcs.report_to_review = True

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "repo", "no code review system")


def test_multiple_errors_submit_git_params_commit_message():
    settings = create_settings("submit", "git")
    settings.Submit.commit_message = None
    settings.GitVcs.repo = None
    settings.GitSubmitVcs.user = None
    settings.GitSubmitVcs.email = None

    assert_incorrect_parameter(settings, "COMMIT_MESSAGE", "repo", "git user name", "git user email")


def test_multiple_errors_main_gerrit_repo_and_build_id():
    settings = create_settings("main", "gerrit")
    settings.TeamcityServer.build_id = None
    settings.GitVcs.repo = None

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "repo")

    settings = create_settings("main", "gerrit")
    settings.TeamcityServer.build_id = None
    settings.GitVcs.repo = "http://"

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "ssh protocol")

    settings = create_settings("main", "gerrit")
    settings.TeamcityServer.build_id = None
    settings.GitVcs.repo = "ssh://127.0.0.1"

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "user name for accessing gerrit")


def test_multiple_errors_main_gerrit_refspec_and_build_id():
    settings = create_settings("main", "gerrit")
    settings.TeamcityServer.build_id = None
    settings.GitVcs.refspec = None
    settings.GitMainVcs.checkout_id = "HEAD"

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "Git refspec for gerrit", "git checkout ID")

    settings = create_settings("main", "gerrit")
    settings.TeamcityServer.build_id = None
    settings.GitVcs.refspec = "ABCDEF"
    settings.GitMainVcs.checkout_id = "HEAD"

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "Git refspec for gerrit", "git checkout ID")


def test_multiple_errors_main_github_and_build_id():
    settings = create_settings("main", "ghapp")
    settings.TeamcityServer.build_id = None
    settings.GitVcs.repo = None
    settings.GitMainVcs.checkout_id = None
    settings.GithubToken.integration_id = None
    settings.GithubToken.key = None
    settings.GithubTokenWithInstallation.installation_id = None
    settings.GithubAppMainVcs.check_id = None

    assert_incorrect_parameter(settings, "id of the build on TeamCity", "git repo", "checkout id for github",
                               "GitHub App ID", "GitHub App private key", "GitHub App installation ID",
                               "GitHub Check Run ID")


def test_multiple_errors_githubhandler():
    settings = create_settings("github-handler", "github")

    settings.GithubHandler.event = None
    settings.GithubHandler.payload = None
    settings.GithubHandler.trigger_url = None
    settings.GithubToken.integration_id = None
    settings.GithubToken.key = None

    assert_incorrect_parameter(settings, "GitHub web-hook event", "build trigger URL", "GitHub web-hook payload",
                               "GitHub App ID", "GitHub App private key")


def test_multiple_errors_poll_p4_params_and_jenkins():
    settings = create_settings("poll", "p4")
    settings.PerforceVcs.port = None
    settings.PerforceVcs.user = None
    settings.PerforceVcs.password = None
    settings.PerforceWithMappings.project_depot_path = None
    settings.AutomationServer.type = "jenkins"
    settings.JenkinsServerForTrigger.trigger_url = None

    assert_incorrect_parameter(settings, "port", "user name", "password", "mappings", "Jenkins url for triggering")
