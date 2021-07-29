import os
import re

from .base_output import BaseOutput


__all__ = [
    "HtmlOutput"
]


class HtmlOutput(BaseOutput):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = None

    def set_artifact_dir(self, artifacts_dir):
        self.filename = os.path.join(artifacts_dir, "log.html")

    def open_block(self, num_str, name):
        self.log(name) # stub

    def close_block(self, num_str, name, status):
        self.log(name) # stub

    def report_error(self, description):
        self.log(description) # stub

    def report_skipped(self, message):
        self.log(message) # stub

    def report_step(self, message, status):
        self.log(message) # stub

    def change_status(self, message):
        self.log(message) # stub

    def log_exception(self, line):
        self.log(line) # stub

    def log_stderr(self, line):
        self.log(line) # stub

    def log(self, line):
        if self._is_log_start(line):
            self._write_html_header()
        self._write_to_file(line) # stub
        if self._is_log_end(line):
            self._write_html_footer()

    def log_external_command(self, command):
        self.log(command) # stub

    def log_shell_output(self, line):
        self.log(line) # stub

    @staticmethod
    def _is_log_start(line):
        log_start_pattern = r"^Universum \d+\.\d+\.\d+ started execution$"
        return re.match(log_start_pattern, line)

    @staticmethod
    def _is_log_end(line):
        log_end_pattern = r"^Universum \d+\.\d+\.\d+ finished execution$"
        return re.match(log_end_pattern, line)

    def _write_html_header(self):
        header = '''
            <!DOCTYPE html>
            <html>
                <head></head>
                <body>
                    <pre>
        '''
        self._write_to_file(header)

    def _write_html_footer(self):
        footer = '''
                    </pre>
                </body>
            </html>
        '''
        self._write_to_file(footer)

    def _write_to_file(self, line):
        if not self.filename:
            raise RuntimeError("Artifact directory was not set")
        with open(self.filename, 'a') as file:
            file.write(line)
            file.write(os.linesep)
