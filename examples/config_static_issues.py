from _universum.configuration_support import Variations

configs = Variations([dict(name="Run static pylint", code_report=True, command=[
    "universum_static", "--type", "pylint", "--files", "static_issues.py"])])


if __name__ == '__main__':
    print configs.dump()
