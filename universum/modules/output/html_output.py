import os

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
        self._write_to_file(line) # stub

    def log_external_command(self, command):
        self.log(command) # stub

    def log_shell_output(self, line):
        self.log(line) # stub

    def log_execution_start(self, title, version):
        self._write_html_header()
        self._write_to_file(self._build_execution_start_msg(title, version))

    def log_execution_finish(self, title, version):
        self._write_to_file(self._build_execution_finish_msg(title, version))
        self._write_html_footer()

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
