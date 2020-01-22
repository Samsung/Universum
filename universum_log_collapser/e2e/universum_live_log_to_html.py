#!/usr/bin/python3

import os
import subprocess
import re


def run_universum():
    os.environ["PYTHONUNBUFFERED"] = "1"
    cmd = """universum --clean-build --vcs-type=none --server-type=local --out-type=term 
        --launcher-output=console --file-source-dir=. --launcher-config-path=./universum_config/configs.py"""
    stdout = launch_process(*cmd.split())
    return re.sub("\\[.+?m", "", stdout)


def run_plugin_cli(log):
    java_cmd = "java -cp "
    for jar in os.listdir(os.path.join(os.getcwd(), "jar")):
        java_cmd += "./jar/" + jar + ":"
    java_cmd += " io.jenkins.plugins.universum_log_collapser.Main"
    return launch_process(*java_cmd.split(), log)


def launch_process(*args):
    popen = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert popen.wait() == 0, popen.stderr.read().decode()
    stdout = popen.stdout.read().decode()
    assert stdout
    return stdout


def write_to_html(log):
    html_start = """
    <html>
        <body>
            <script src="../plugin/src/main/resources/io/jenkins/plugins/universum_log_collapser/Note/script.js"></script>
            <link rel="stylesheet" type="text/css" href="../plugin/src/main/resources/io/jenkins/plugins/universum_log_collapser/Note/style.css">
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
