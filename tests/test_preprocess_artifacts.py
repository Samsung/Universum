import inspect
import os

from universum import __main__


def test_no_artifact_prebuild_clean(tmpdir):
    config_file = write_config_file(tmpdir, artifact_prebuild_clean=True)
    artifacts_dir = tmpdir.join("artifacts")

    check_universum_executed_successfully(tmpdir, artifacts_dir, config_file)
    check_step_artifact_present(artifacts_dir)


def test_no_artifact_no_prebuild_clean(tmpdir):
    config_file = write_config_file(tmpdir, artifact_prebuild_clean=False)
    artifacts_dir = tmpdir.join("artifacts")

    check_universum_executed_successfully(tmpdir, artifacts_dir, config_file)
    check_step_artifact_present(artifacts_dir)


def test_existing_artifact_prebuild_clean(tmpdir):
    config_file = write_config_file(tmpdir, artifact_prebuild_clean=True)
    artifacts_dir = tmpdir.join("artifacts")

    create_artifact_file(tmpdir)
    check_universum_executed_successfully(tmpdir, artifacts_dir, config_file)
    check_step_artifact_present(artifacts_dir)


def test_existing_artifact_no_prebuild_clean(tmpdir):
    config_file = write_config_file(tmpdir, artifact_prebuild_clean=False)
    artifacts_dir = tmpdir.join("artifacts")

    create_artifact_file(tmpdir)
    check_universum_failed(tmpdir, artifacts_dir, config_file)
    check_step_artifact_absent(artifacts_dir)


def write_config_file(tmpdir, artifact_prebuild_clean):
    config = inspect.cleandoc(f"""
        from universum.configuration_support import Configuration, Step
        step = Step(name='Step', command=['touch', 'artifact'], artifacts='artifact', 
                    artifact_prebuild_clean={artifact_prebuild_clean})
        configs = Configuration([step])
    """)

    config_file = tmpdir.join("configs.py")
    config_file.write_text(config, "utf-8")

    return config_file


def check_universum_executed_successfully(tmpdir, artifacts_dir, config_file):
    return_code = launch_universum(tmpdir, artifacts_dir, config_file)
    assert return_code == 0


def check_universum_failed(tmpdir, artifacts_dir, config_file):
    return_code = launch_universum(tmpdir, artifacts_dir, config_file)
    assert return_code == 1


def launch_universum(tmpdir, artifacts_dir, config_file):
    params = ["-vt", "none",
              "-fsd", str(tmpdir),
              "-ad", str(artifacts_dir),
              "--clean-build",
              "-o", "console",
              "-cfg", str(config_file)]
    return __main__.main(params)


def check_step_artifact_present(artifacts_dir):
    step_artifact = artifacts_dir.join("artifact")
    assert os.path.exists(step_artifact)


def check_step_artifact_absent(artifacts_dir):
    step_artifact = artifacts_dir.join("artifact")
    assert not os.path.exists(step_artifact)


def create_artifact_file(tmpdir):
    artifact_file = tmpdir.join("artifact")
    open(artifact_file, "w").close()
