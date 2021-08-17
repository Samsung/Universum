import os

from .base_output import BaseOutput


__all__ = [
    "HtmlOutput"
]


class HtmlOutput(BaseOutput):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._filename = None
        self.artifact_dir_ready = False
        self._log_buffer = list()

    def set_artifact_dir(self, artifact_dir):
        self._filename = os.path.join(artifact_dir, "log.html")

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
        self._log_line(line) # stub

    def log_external_command(self, command):
        self.log(command) # stub

    def log_shell_output(self, line):
        self.log(line) # stub

    def log_execution_start(self, title, version):
        self._log_html_header()
        self._log_line(self._build_execution_start_msg(title, version))

    def log_execution_finish(self, title, version):
        self._log_line(self._build_execution_finish_msg(title, version))
        self._log_html_footer()

    def _log_html_header(self):
        header = '''
            <!DOCTYPE html>
            <html>
                <head></head>
                <body>
                    <pre>
        '''
        self._log_line(header)

    def _log_html_footer(self):
        footer = '''
                    </pre>
                </body>
            </html>
        '''
        self._log_line(footer)

    def _log_line(self, line):
        if not self._filename:
            raise RuntimeError("Artifact directory was not set")
        if not self.artifact_dir_ready:
            self._log_buffer.append(line)
            return
        if self._log_buffer:
            self._log_and_clear_buffer()
        self._write_to_file(line)

    def _log_and_clear_buffer(self):
        for buffered_line in self._log_buffer:
            self._write_to_file(buffered_line)
        self._log_buffer = list()

    def _write_to_file(self, line):
        with open(self._filename, "a") as file:
            file.write(line)
            file.write(os.linesep)
