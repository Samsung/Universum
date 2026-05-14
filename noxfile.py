# pylint: disable = import-error

import os
import pathlib
import nox


report = "Here are the results of regression testing:"


def add_report_line(text):
    global report
    report += "\n" + text


def send_report():
    print("This is report file: ", os.environ["GITHUB_STEP_SUMMARY"])
    pathlib.Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(report)


# @nox.session(python=["3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"])
@nox.session(python=["3.8", "3.12"])
def test(session):
    try:
        logfile = pathlib.Path("logs", f"python{session.python}.txt")
        logfile.parent.mkdir(exist_ok=True, parents=True)
        logfile.write_text(f"Python{session.python} test logs\n")
        with logfile.open("a") as log:
            session.run("make", "rebuild", stdout=log, external=True)
            session.install(".[test]", stdout=log, silent=False)
            session.run("make", "test", stdout=log, external=True, env={"UNIVERSUM_NOX_REGRESSION": "True"})
        add_report_line(f"\U00002600 testing for Python {session.python} succeeded")
    except nox.command.CommandFailed:
        add_report_line(f"\U00002601 testing for Python {session.python} failed")
    session.run("mv", "junit_results.xml", f"junit_results_{session.python}.xml", external=True)


@nox.session()
def clean(session):
    try:
        session.run("docker", "image", "prune", "-f", external=True)
    except nox.command.CommandFailed:
        add_report_line("\U0000274c final cleaning failed!")
    send_report()
