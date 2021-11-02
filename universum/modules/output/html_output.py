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
        self._log_buffer = []
        self._block_level = 0

    def set_artifact_dir(self, artifact_dir):
        self._filename = os.path.join(artifact_dir, "log.html")

    def open_block(self, num_str, name):
        opening_html = f'<input type="checkbox" id="{num_str}" class="hide"/>' + \
            f'<label for="{num_str}"><span class="sectionLbl">'
        closing_html = "</span></label><div>"
        name_html = f'<span class="sectionTitle">{name}</span>'
        self._log_line(f"{opening_html}{num_str} {name_html}{closing_html}", with_line_separator=False)
        self._block_level += 1

    def close_block(self, num_str, name, status):
        self._block_level -= 1
        indent = "  " * self._block_level
        closing_html = '</div><span class="nl"></span>'
        status_html = f'<span class="{status.lower()}Status">[{status}]</span>'
        self._log_line(f"{indent} \u2514 {status_html}{closing_html}", with_line_separator=False)
        self._log_line("")

    def report_error(self, description):
        pass

    def report_skipped(self, message):
        self._log_line(f'<span class="skipped">{message}</span>')

    def report_step(self, message, status):
        if message.endswith(status):
            message = message[:-len(status)]
            message += f'<span class="{status.lower()}Status">{status}</span>'
        self.log(message)

    def change_status(self, message):
        pass

    def log_exception(self, line):
        self._log_line(f'<span class="exceptionTag">Error:</span> {line}')

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
        html_header = f"<!DOCTYPE html><html><head>{head_content}</head><body>"
        html_header += '<input type="checkbox" id="dark-checkbox"><label for="dark-checkbox"></label><pre>'
        self._log_line(html_header)
        self.log(self._build_execution_start_msg(title, version))

    def log_execution_finish(self, title, version):
        self.log(self._build_execution_finish_msg(title, version))
        html_footer = "</pre></body></html>"
        self._log_line(html_footer)

    def _log_line(self, line, with_line_separator=True):
        if with_line_separator and not line.endswith(os.linesep):
            line += os.linesep
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
        self._log_buffer = []

    def _write_to_file(self, line):
        with open(self._filename, "a", encoding="utf-8") as file:
            file.write(self._build_indent())
            file.write(line)

    def _build_indent(self):
        indent_str = []
        for x in range(0, self._block_level):
            indent_str.append("  " * x)
            indent_str.append(" |   ")
        return "".join(indent_str)

    @staticmethod
    def _build_html_head():
        css_rules = '''
            body {
                background-color: white;
                color: black;
                margin: 0;
                height: 100%;
                min-height: 100vh;
                display: flex;
            }

            .sectionTitle {
                color: darkslateblue;
                font-weight: bold;
            }
            .successStatus {
                color: green;
                font-weight: bold;
            }
            .failedStatus {
                color: red;
                font-weight: bold;
            }
            .skippedStatus {
                color: red;
                font-weight: bold;
            }
            .skipped {
                color: darkcyan;
            }
            .exceptionTag {
                color: darkred;
            }

            .hide {
                display: none;
            }
            .hide + label ~ div {
                display: none;
            }
            .hide + label {

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

            #dark-checkbox {
                display: none;
            }

            pre {
                padding: 20px 20px 65px 20px;
                margin: 0;
                width: 100%;
            }

            #dark-checkbox:checked+label+pre {
                background-color: black;
                color: rgb(219, 198, 198);
            }

            #dark-checkbox:checked+label+pre .sectionTitle {
                color: #2b7cdf;
            }

            #dark-checkbox+label {
                position: fixed;
                right: 15px;
                bottom: 15px;
                width: 95px;
                height: 30px;
                border-radius: 20px;
                background-color: white;
                color: gray;
                border: gray 1px solid;
                font: 12px sans;
                cursor: pointer;
            }

            #dark-checkbox:checked+label {
                background-color: black;
                color: white;
            }

            #dark-checkbox+label::before {
                position: absolute;
                content: "";
                height: 22px;
                width: 22px;
                left: 4px;
                bottom: 4px;
                background-color: gray;
                transition: .3s;
                border-radius: 50%;
            }

            #dark-checkbox:checked+label::before {
                background-color: white;
                transform: translateX(65px);
            }

            #dark-checkbox+label::after {
                content: 'Light';
                display: block;
                position: absolute;
                transform: translate(-50%, -50%);
                top: 50%;
                left: 50%;
            }

            #dark-checkbox:checked+label::after {
                content: 'Dark';
            }
        '''
        head = []
        head.append('<meta content="text/html;charset=utf-8" http-equiv="Content-Type">')
        head.append('<meta content="utf-8" http-equiv="encoding">')
        head.append(f"<style>{css_rules}</style>")
        return "".join(head)
