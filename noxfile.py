# pylint: disable = import-error

import os
import nox
import requests


report = "Here are the results of regression testing:"


def add_report_line(text):
    global report
    report += "\n" + text


def send_report():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",
                  data={"chat_id": chat, "text": report})


@nox.session(python=["3.6", "3.7", "3.8", "3.9"])
def test(session):
    try:
        session.run("make", "rebuild", silent=True, external=True)
        session.install("universum[test]")
        session.run("make", "test", external=True)
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
