from _universum.configuration_support import Variations

env_name = "virtual_universe"


def run_virtual(cmd):
    return ["env", "-i", "bash -c 'source {}/bin/activate; {}'".format(env_name, cmd)]


pylint_cmd = "universum_pylint --python-version 2 --rcfile pylintrc " + \
             "--files *.py _universum/ tests/ analyzers/ --result-file '${CODE_REPORT_FILE}'"

configs = Variations([dict(name="Update Docker images", command=["make", "images"]),
                      dict(name="Create virtual environment",
                           command=["python2", "-m", "virtualenv", env_name, "--system-site-packages"]),
                      dict(name="Install development",
                           command=run_virtual("pip --default-timeout=1200 install .[development]")),
                      dict(name="Make", artifacts="doc/_build", command=run_virtual("make")),
                      dict(name="Install tests", artifacts="junit_results.xml",
                           command=run_virtual("pip --default-timeout=1200 install .[test]")),
                      dict(name="Make tests", artifacts="htmlcov",
                           command=run_virtual("export LANG=en_US.UTF-8; make test")),
                      dict(name="Run static pylint", code_report=True,
                           command=run_virtual("pip uninstall -y universum; " + pylint_cmd))])

if __name__ == '__main__':
    print configs.dump()
