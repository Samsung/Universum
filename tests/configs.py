
import os
from _universum.configuration_support import Variations

env_name = "virtual_universe"


def run_virtual(cmd):
    return ["env", "-i", "PATH=" + os.getenv("PATH"), "bash", "-c", "source {}/bin/activate; {}".format(env_name, cmd)]


pylint_cmd = "universum_pylint --python-version 3 --rcfile pylintrc " + \
             "--files *.py _universum/ tests/ analyzers/ --result-file '${CODE_REPORT_FILE}'"

configs = Variations([dict(name="Update Docker images", command=["make", "images"]),
                      dict(name="Create virtual environment",
                           command=["python3.7", "-m", "virtualenv", env_name, "--system-site-packages"]),
                      dict(name="Install development",
                           command=run_virtual("pip --default-timeout=1200 install .[development]")),
                      dict(name="Make", artifacts="doc/_build", command=run_virtual("make")),
                      dict(name="Install tests", artifacts="junit_results.xml",
                           command=run_virtual("pip --default-timeout=1200 install .[test]")),
                      dict(name="Make tests", artifacts="htmlcov",
                           command=run_virtual("export LANG=en_US.UTF-8; make test")),
                      dict(name="Run static pylint", code_report=True,
                           command=run_virtual("pip uninstall -y universum; " + pylint_cmd)),
                      dict(name="Run Jenkins plugin Java tests",
                           artifacts="universum_log_collapser/plugin/target/surefire-reports/*.xml",
                           command=["mvn", "-B", "test"], directory="universum_log_collapser/plugin"),
                      dict(name="Prepare Jenkins plugin Javascript tests project",
                           command=["npm", "install"], directory="universum_log_collapser/e2e"),
                      dict(name="Run Jenkins plugin Javascript tests",
                           command=["npm", "test"], directory="universum_log_collapser/e2e")])

if __name__ == '__main__':
    print(configs.dump())
