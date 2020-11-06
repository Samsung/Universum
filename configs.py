#!/usr/bin/env python

import os
import sys
from universum.configuration_support import Variations

env_name = "virtual_universe"
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
python = f"python{python_version}"


def run_virtual(cmd):
    return ["env", "-i", "PATH=" + os.getenv("PATH"), "bash", "-c", f"source {env_name}/bin/activate && {cmd}"]


def pip_install(module_name):
    return "python -m pip --default-timeout=1200 install --progress-bar off -U " + module_name


configs = Variations([dict(name="Update Docker images", command=["make", "images"]),
                      dict(name="Update Pylint", command=[python, "-m", "pip", "install",
                                                          "-U", "--user", "--progress-bar", "off", "pylint"]),
                      dict(name="Create virtual environment", command=[python, "-m", "venv", env_name]),

                      dict(name="Install Universum for tests", artifacts="junit_results.xml",
                           command=run_virtual(pip_install(".[test]"))),
                      dict(name="Make", artifacts="doc/_build",
                           command=run_virtual("make")),
                      dict(name="Make tests", artifacts="htmlcov",
                           command=run_virtual("export LANG=en_US.UTF-8; make test")),

                      dict(name="Run static pylint", code_report=True,
                           command=[python, "-m", "universum.analyzers.pylint",
                                    f"--python-version={python_version}",
                                    "--rcfile=pylintrc", "--result-file=${CODE_REPORT_FILE}",
                                    "--files", "*.py", "universum/", "tests/"]),
                      dict(name="Run static type checker", code_report=True,
                           command=run_virtual("make mypy")),

                      dict(name="Run Jenkins plugin Java tests",
                           artifacts="universum_log_collapser/universum_log_collapser/target/surefire-reports/*.xml",
                           command=["mvn", "-B", "package"], directory="universum_log_collapser/universum_log_collapser"),
                      dict(name="Run Jenkins plugin CLI version",
                           command=["mvn", "-B", "compile", "assembly:single"],
                           artifacts="universum_log_collapser/universum_log_collapser/target/universum_log_collapser.hpi",
                           directory="universum_log_collapser/universum_log_collapser"),

                      dict(name="Generate HTML for JavaScript tests",
                           command=[python, "universum_log_collapser/e2e/universum_live_log_to_html.py"]),
                      dict(name="Prepare Jenkins plugin JavaScript tests project",
                           command=["npm", "install"], directory="universum_log_collapser/e2e"),
                      dict(name="Run Jenkins plugin JavaScript tests",
                           command=["npm", "test"], directory="universum_log_collapser/e2e")])

if __name__ == '__main__':
    print(configs.dump())
