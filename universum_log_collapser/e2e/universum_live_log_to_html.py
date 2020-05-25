#!/usr/bin/env python3.7

import os
import subprocess
import re


def run_universum():
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = """python3.7 -m universum --clean-build --vcs-type=none --server-type=local --out-type=term 
        --launcher-output=console --file-source-dir=. --launcher-config-path=universum_log_collapser/e2e/universum_config/configs.py"""
    stdout = launch_process(*cmd.split(), env=env)
    return re.sub("\\[.+?m", "", stdout)


def run_plugin_cli(log):
    jar_path = os.path.join(os.getcwd(), "universum_log_collapser", "universum_log_collapser", "target",
        "universum_log_collapser-jar-with-dependencies.jar")
    assert os.path.exists(jar_path), "Run maven build for CLI jar first"
    return launch_process("java", "-cp", jar_path, "io.jenkins.plugins.universum_log_collapser.Main", log)


def launch_process(*args, env=None):
    popen = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    assert popen.wait() == 0, popen.stderr.read().decode()
    stdout = popen.stdout.read().decode()
    assert stdout
    return stdout


def write_to_html(log):
    html_start = """
    <html>
        <body>
            <script src="../universum_log_collapser/src/main/resources/io/jenkins/plugins/universum_log_collapser/Note/script.js"></script>
            <link rel="stylesheet" type="text/css" href="../universum_log_collapser/src/main/resources/io/jenkins/plugins/universum_log_collapser/Note/style.css">
            <pre class="console-output">
    """
    html_end = """
            </pre>
        </body>
    </html>
    """

    with open("generated.html", "w") as file:
        file.write(html_start + log + html_end)


if __name__ == "__main__":
    raw_log = run_universum()
    wrapped_log = run_plugin_cli(raw_log)
    write_to_html(wrapped_log)
