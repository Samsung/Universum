import os
import nox
import requests


report = "Here are the results of regression testing:"


def add_report_line(text):
    global report
    report += "\n" + text


def send_report():
    global report
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",
                  data={"chat_id": chat, "text": report})


@nox.session(python=["3.6", "3.7", "3.8", "3.9"])
def test(session):
    pass
    # try:
    #     session.run("make", "rebuild", silent=True, external=True)
    #     session.install("universum[test]")
    #     session.run("make", "test", external=True)
    #     add_report_line(f"\U00002b50 testing for Python {session.python} succeeded")
    # except nox.command.CommandFailed:
    #     add_report_line(f"\U0000274c testing for Python {session.python} failed")
    # session.run("mv", "junit_results.xml", f"junit_results_{session.python}.xml", external=True)


@nox.session()
def clean(session):
    add_report_line("\U00002600 is good")
    add_report_line("\U00002601 is bad")
    add_report_line("\U0001F4A8 is very bad")
    send_report()
    try:
        session.run("docker", "image", "prune", "-f", external=True)
    except nox.command.CommandFailed:
        add_report_line("\U00002716 final cleaning failed!")
    send_report()
