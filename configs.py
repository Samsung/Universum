#!/usr/bin/env python3.7

import os
from universum.configuration_support import Variations

env_name = "virtual_universe"


def run_virtual(cmd):
    return ["env", "-i", "PATH=" + os.getenv("PATH"), "bash", "-c", "source {}/bin/activate && {}".format(env_name, cmd)]


def pip_install(module_name):
    return "python3.7 -m pip --default-timeout=1200 install --progress-bar off -U " + module_name


configs = Variations([dict(name="Update Docker images", command=["make", "images"]),
                      dict(name="Update Pylint", command=["python3.7", "-m", "pip", "install", "-U", "--user",
                                                          "--progress-bar", "off", "pylint"]),
                      dict(name="Create virtual environment",
                           command=["python3.7", "-m", "venv", env_name]),
                      dict(name="Install development", command=run_virtual(pip_install(".[development]"))),
                      dict(name="Make", artifacts="doc/_build", command=run_virtual("make")),

                      dict(name="Install tests", artifacts="junit_results.xml",
                           command=run_virtual(pip_install(".[test]"))),
                      dict(name="Make tests", artifacts="htmlcov",
                           command=run_virtual("export LANG=en_US.UTF-8; make test")),

                      dict(name="Run static pylint", code_report=True,
                           command=["python3.7", "-m", "universum.analyzers.pylint", "--python-version=3.7",
                                    "--rcfile=pylintrc", "--result-file=${CODE_REPORT_FILE}",
                                    "--files", "*.py", "universum/", "tests/"]),
                      dict(name="Run static type checker", code_report=True,
                           command=["python3.7", "-m", "mypy", "universum/main.py"]),

                      dict(name="Run Jenkins plugin Java tests",
                           artifacts="universum_log_collapser/universum_log_collapser/target/surefire-reports/*.xml",
                           command=["mvn", "-B", "test"], directory="universum_log_collapser/universum_log_collapser"),
                      dict(name="Run Jenkins plugin CLI version",
                           command=["mvn", "-B", "compile", "assembly:single"],
                           directory="universum_log_collapser/universum_log_collapser"),
                      dict(name="Generate HTML for JavaScript tests",
                           command=["universum_log_collapser/e2e/universum_live_log_to_html.py"]),
                      dict(name="Prepare Jenkins plugin JavaScript tests project",
                           command=["npm", "install"], directory="universum_log_collapser/e2e"),
                      dict(name="Run Jenkins plugin JavaScript tests",
                           command=["npm", "test"], directory="universum_log_collapser/e2e")])

if __name__ == '__main__':
    print(configs.dump())
