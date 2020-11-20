import nox


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.run("make", "rebuild", silent=True, external=True)
    session.install("universum[test]")
    session.run("make", "test", external=True)
