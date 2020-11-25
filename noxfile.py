import nox


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.run("make", "rebuild", silent=True, external=True)
    session.install("universum[test]")
    session.run("make", "test", external=True, success_codes=[0, 2])
    session.run("mv", "junit_results.xml", f"junit_results_{session.python}.xml", external=True)


@nox.session()
def clean(session):
    session.run("docker", "image", "prune", "-f", external=True)
