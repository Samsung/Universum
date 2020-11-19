import nox  # pylint: disable = import-error


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.run("make", "rebuild")
    session.install("universum[test]")
    session.run("make", "test")
