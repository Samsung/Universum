#!/usr/bin/env python

import os
import sys
from universum.configuration_support import Step, Variations

env_name = "virtual_universe"
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
python = f"python{python_version}"


def run_virtual(cmd):
    return ["env", "-i", "PATH=" + os.getenv("PATH"), "bash", "-c", f"source {env_name}/bin/activate && {cmd}"]


def pip_install(module_name):
    return "python -m pip --default-timeout=1200 install --progress-bar off -U " + module_name


configs = Variations([Step(name="Create virtual environment", command=[python, "-m", "venv", env_name]),
                      Step(name="Update Docker images", command=run_virtual("make images")),

                      Step(name="Install Universum for tests",
                           command=run_virtual(pip_install(".[test]"))),
                      Step(name="Make", artifacts="doc/_build",
                           command=run_virtual("make")),
                      Step(name="Make tests", artifacts="htmlcov",
                           command=run_virtual("export LANG=en_US.UTF-8; make test")),
                      Step(name="Collect test results", artifacts="junit_results.xml"),

                      Step(name="Run static pylint", code_report=True,
                           command=run_virtual(f"{python} -m universum.analyzers.pylint "
                                               f"--python-version={python_version} --rcfile=pylintrc "
                                               "--result-file=\"${CODE_REPORT_FILE}\" --files *.py universum/ tests/")),
                      Step(name="Run static type checker", code_report=True,
                           command=run_virtual(f"{python} -m universum.analyzers.mypy --python-version={python_version} "
                                               "--result-file=\"${CODE_REPORT_FILE}\" --files *.py universum/ tests/"))])

if __name__ == '__main__':
    print(configs.dump())
