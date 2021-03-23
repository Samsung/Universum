import os
import nox
import requests


def report(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",
                  data={"chat_id": chat, "text": text})


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.run("make", "rebuild", silent=True, external=True)
    session.install("universum[test]")
    try:
        session.run("make", "test", external=True)
        report(f"Regression testing for Python {session.python} succeeded")
    except nox.command.CommandFailed:
        report(f"Regression testing for Python {session.python} failed")
    session.run("mv", "junit_results.xml", f"junit_results_{session.python}.xml", external=True)


@nox.session()
def clean(session):
    session.run("docker", "image", "prune", "-f", external=True)
