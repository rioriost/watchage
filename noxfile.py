import nox

nox.options.python = "3.13"
nox.options.default_venv_backend = "uv"


@nox.session(python=["3.13"], tags=["lint"])
def lint(session):
    session.install("ruff")
    session.run("uv", "run", "ruff", "check")
    session.run("uv", "run", "ruff", "format")


@nox.session(python=["3.13"], tags=["mypy"])
def mypy(session):
    session.install(".")
    session.install("mypy")
    session.run("uv", "run", "mypy", "app.py")


@nox.session(python=["3.13"], tags=["pytest"])
def pytest(session):
    session.install(".")
    session.install("pytest", "pytest-cov")
    test_files = ["test.py"]
    session.run(
        "uv",
        "run",
        "pytest",
        "--maxfail=1",
        "--cov=watchage",
        "--cov-report=term",
        *test_files,
    )
