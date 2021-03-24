import os
import nox
import requests


report = "Here are the results of regression testing:"


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    global report
    try:
        session.run("make", "rebuild", silent=True, external=True)
        session.install("universum[test]")
        session.run("make", "test", external=True)
        report += f"\n\U00002b50 testing for Python {session.python} succeeded"
    except nox.command.CommandFailed:
        report += f"\n\U0000274c testing for Python {session.python} failed"
    session.run("mv", "junit_results.xml", f"junit_results_{session.python}.xml", external=True)


@nox.session()
def clean(session):
    global report
    try:
        session.run("docker", "image", "prune", "-f", external=True)
    except nox.command.CommandFailed:
        report += "\n\U00002716 final cleaning failed!"

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",
                  data={"chat_id": chat, "text": report})
