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
        self._block_level = 0

    def set_artifact_dir(self, artifact_dir):
        self._filename = os.path.join(artifact_dir, "log.html")

    def open_block(self, num_str, name):
        opening_html = f'<input type="checkbox" id="{num_str}" class="hide"/>' + \
            f'<label for="{num_str}"><span class="sectionLbl">'
        closing_html = "</span></label><div>"
        self._log_line(f"{opening_html}{num_str} {name}{closing_html}", with_line_separator=False)
        self._block_level += 1

    def close_block(self, num_str, name, status):
        self._block_level -= 1
        indent = "  " * self._block_level
        closing_html = '</div><span class="nl"></span>'
        self._log_line(f"{indent} \u2514 [{status}]{closing_html}", with_line_separator=False)
        self._log_line("")

    def report_error(self, description):
        pass

    def report_skipped(self, message):
        self._log_line(message)

    def report_step(self, message, status):
        self.log(message)

    def change_status(self, message):
        pass

    def log_exception(self, line):
        self._log_line(f"Error: {line}")

    def log_stderr(self, line):
        self._log_line(f"stderr: {line}")

    def log(self, line):
        self._log_line(f"==> {line}")

    def log_external_command(self, command):
        self._log_line(f"$ {command}")

    def log_shell_output(self, line):
        self._log_line(line)

    def log_execution_start(self, title, version):
        head_content = self._build_html_head()
        html_header = f"<!DOCTYPE html><html><head>{head_content}</head><body><pre>"
        self._log_line(html_header)
        self.log(self._build_execution_start_msg(title, version))

    def log_execution_finish(self, title, version):
        self.log(self._build_execution_finish_msg(title, version))
        html_footer = "</pre></body></html>"
        self._log_line(html_footer)

    def _log_line(self, line, with_line_separator=True):
        line = f"{line}{os.linesep}" if with_line_separator else line
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
            file.write(self._build_indent())
            file.write(line)

    def _build_indent(self):
        indent_str = list()
        for x in range(0, self._block_level):
            indent_str.append("  " * x)
            indent_str.append(" |   ")
        return "".join(indent_str)

    def _build_html_head(self):
        css_rules = '''
            .sectionLbl {
                color: black;
            }
            .sectionLbl span {
                color: black !important;
            }

            .hide {
                display: none;
            }
            .hide + label ~ div {
                display: none;
            }
            .hide + label {
                color: black;
                cursor: pointer;
                display: inline-block;
            }
            .hide:checked + label + div {
                display: block;
            }

            .hide + label + div + .nl {
                display: block;
            }
            .hide:checked + label + div + .nl::after {
                display: none;
            }

            .hide + label .sectionLbl::before {
                content: "[+] ";
            }
            .hide:checked + label .sectionLbl::before {
                content: "[-] ";
            }
        '''
        head = list()
        head.append('<meta content="text/html;charset=utf-8" http-equiv="Content-Type">')
        head.append('<meta content="utf-8" http-equiv="encoding">')
        head.append(f"<style>{css_rules}</style>")
        return "".join(head)
