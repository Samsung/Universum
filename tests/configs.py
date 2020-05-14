
import os
from _universum.configuration_support import Variations

env_name = "virtual_universe"


def run_virtual(cmd):
    return ["env", "-i", "PATH=" + os.getenv("PATH"), "bash", "-c", "source {}/bin/activate; {}".format(env_name, cmd)]


pylint_cmd = "universum_pylint --python-version 3 --rcfile pylintrc " + \
             "--files *.py universum/ tests/ analyzers/ --result-file '${CODE_REPORT_FILE}'"

configs = Variations([dict(name="Update Docker images", command=["make", "images"]),
                      dict(name="Create virtual environment",
                           command=["python3.7", "-m", "venv", env_name]),
                      dict(name="Install development",
                           command=run_virtual("python3.7 -m pip --default-timeout=1200 install .[development] -U")),
                      dict(name="Make", artifacts="doc/_build", command=run_virtual("make")),

                      dict(name="Install tests", artifacts="junit_results.xml",
                           command=run_virtual("python3.7 -m pip --default-timeout=1200 install .[test] -U")),
                      dict(name="Make tests", artifacts="htmlcov",
                           command=run_virtual("export LANG=en_US.UTF-8; make test")),
                      dict(name="Run static pylint", code_report=True,
                           command=run_virtual("python3.7 -m pip uninstall -y universum; " + pylint_cmd)),

                      dict(name="Run Jenkins plugin Java tests",
                           artifacts="universum_log_collapser/universum_log_collapser/target/surefire-reports/*.xml",
                           command=["mvn", "-B", "test"], directory="universum_log_collapser/universum_log_collapser"),
                      dict(name="Run Jenkins plugin CLI version",
                           command=["mvn", "-B", "compile", "assembly:single"],
                           directory="universum_log_collapser/universum_log_collapser"),
                      dict(name="Generate HTML for JavaScript tests",
                           command=["./universum_live_log_to_html.py"],
                           directory="universum_log_collapser/e2e"),
                      dict(name="Prepare Jenkins plugin JavaScript tests project",
                           command=["npm", "install"], directory="universum_log_collapser/e2e"),
                      dict(name="Run Jenkins plugin JavaScript tests",
                           command=["npm", "test"], directory="universum_log_collapser/e2e")])

if __name__ == '__main__':
    print(configs.dump())
