from _universum.configuration_support import Variations

env_name = "virtual_universe"


def run_virtual(cmd):
    return ["bash", "-c", "source {}/bin/activate; {}".format(env_name, cmd)]


configs = Variations([dict(name="Create virtual environment", command=["virtualenv", env_name]),
                      dict(name="Install development",
                           command=run_virtual("pip --default-timeout=1200 install .[development]")),
                      dict(name="Make", artifacts="doc/_build", command=run_virtual("make")),
                      dict(name="Install tests",
                           command=run_virtual("pip --default-timeout=1200 install .[test]")),
                      dict(name="Make tests", artifacts="htmlcov",
                           command=run_virtual("PYTHONIOENCODING=utf-8 make test")),
                      dict(name="Run static pylint", code_report=True,
                           command=["universum_pylint", "--python-version", "2", "--rcfile", "pylintrc",
                                    "--files", "*.py", "_universum/", "tests/", "analyzers/",
                                    "--result-file", "${CODE_REPORT_FILE}"])])

if __name__ == '__main__':
    print configs.dump()
