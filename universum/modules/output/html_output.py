import os
import re
from datetime import datetime
from re import Match
from typing import Optional, List

from ansi2html import Ansi2HTMLConverter

from .base_output import BaseOutput

__all__ = [
    "HtmlOutput"
]


class HtmlOutput(BaseOutput):
    default_name = "universum_log.html"

    def __init__(self, *args, log_name: str = default_name, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_name: str = log_name
        self._log_path: Optional[str] = None
        self.artifact_dir_ready: bool = False
        self._log_buffer: List[str] = []
        self._block_level: int = 0
        self.module_dir: str = os.path.dirname(os.path.realpath(__file__))
        self.ansi_converter: Ansi2HTMLConverter = Ansi2HTMLConverter(inline=True, escaped=False)

    def log_execution_start(self, title: str, version: str) -> None:
        head_content: str = self._build_html_head()
        html_header: str = f"<!DOCTYPE html><html><head>{head_content}</head><body>"
        html_header += '<input type="checkbox" id="dark-checkbox"><label for="dark-checkbox"></label>'
        html_header += '<input type="checkbox" id="time-checkbox"><label for="time-checkbox"></label>'
        html_header += '<pre>'

        self._log_buffered(html_header)
        self.log(self._build_execution_start_msg(title, version))

    def log_execution_finish(self, title: str, version: str) -> None:
        self.log(self._build_execution_finish_msg(title, version))
        html_footer: str = "</pre>"
        with open(os.path.join(self.module_dir, "html_output.js"), encoding="utf-8") as js_file:
            html_footer += f"<script>{js_file.read()}</script>"
        html_footer += "</body></html>"
        self._log_line(html_footer)

    def log(self, line: str) -> None:
        self._log_line(f"==> {line}")

    def log_error(self, description: str) -> None:
        self._log_line(f'<span class="exceptionTag">Error:</span> {description}')

    def log_external_command(self, command: str) -> None:
        self._log_line(f"$ {command}")

    def log_stdout(self, line: str) -> None:
        self._log_line(line)

    def log_stderr(self, line: str) -> None:
        self._log_line(f'<span class="stderrTag">stderr:</span> {line}')

    def open_block(self, num_str: str, name: str) -> None:
        opening_html: str = f'<input type="checkbox" id="{num_str}" class="hide"/>' + \
                            f'<label for="{num_str}"><span class="sectionLbl">'
        closing_html: str = "</span></label><div>"
        name_html: str = f'<span class="sectionTitle">{name}</span>'
        self._log_line(f"{opening_html}{num_str} {name_html}{closing_html}", with_line_separator=False)
        self._block_level += 1

    def close_block(self, num_str: str, name: str, status: str) -> None:
        self._block_level -= 1
        indent: str = "  " * self._block_level
        closing_html: str = '</div><span class="nl"></span>'
        status_html: str = f'<span class="{status.lower()}Status">[{status}]</span>'
        self._log_line(f"{indent} \u2514 {status_html}{closing_html}", with_line_separator=False)
        self._log_line("")

    def log_skipped(self, message: str) -> None:
        self._log_line(f'<span class="skipped">{message}</span>')

    def log_summary_step(self, step_title: str, has_children: bool, status: str) -> None:
        if not has_children:
            step_title += f' - <span class="{status.lower()}Status">{status}</span>'
        self.log(step_title)

    def report_build_problem(self, description: str) -> None:
        raise RuntimeError("Html output doesn't support reporting build problem.")

    def set_build_status(self, status: str) -> None:
        raise RuntimeError("Html output doesn't support setting build title.")

    def set_artifact_dir(self, artifact_dir: str) -> None:
        self._log_path = os.path.join(artifact_dir, self._log_name)

    def _log_line(self, line: str, with_line_separator: bool = True) -> None:
        if with_line_separator and not line.endswith(os.linesep):
            line += os.linesep
        self._log_buffered(self._build_time_stamp() + self._build_indent() + line)

    def _log_buffered(self, line: str) -> None:
        line = self._wrap_links(line)
        line = self._ansi_codes_to_html(line)
        if not self.artifact_dir_ready:
            self._log_buffer.append(line)
            return
        if self._log_buffer:
            self._log_and_clear_buffer()
        self._write_to_file(line)

    def _log_and_clear_buffer(self) -> None:
        for buffered_line in self._log_buffer:
            self._write_to_file(buffered_line)
        self._log_buffer = []

    def _write_to_file(self, line: str) -> None:
        if not self._log_path:
            raise RuntimeError("Artifact directory was not set")

        with open(self._log_path, "a", encoding="utf-8") as file:
            file.write(line)

    def _build_indent(self) -> str:
        indent_str: List[str] = []
        for x in range(0, self._block_level):
            indent_str.append("  " * x)
            indent_str.append(" |   ")
        return "".join(indent_str)

    def _build_html_head(self) -> str:
        head: List[str] = ['<meta content="text/html;charset=utf-8" http-equiv="Content-Type">',
                           '<meta content="utf-8" http-equiv="encoding">']
        with open(os.path.join(self.module_dir, "html_output.css"), encoding="utf-8") as css_file:
            head.append(f"<style>{css_file.read()}</style>")
        return "".join(head)

    def _ansi_codes_to_html(self, line: str) -> str:
        return self.ansi_converter.convert(line, full=False)

    @staticmethod
    def _wrap_links(line: str) -> str:
        position_shift: int = 0
        pattern = r"(?:http|https|ftp|file|mailto):(?:\\ |\S)+"
        for match in re.finditer(pattern, line):
            link: str = match.group()
            wrapped_link: str = f'<a href="{link}">{link}</a>'
            link_start_pos: int = match.start() + position_shift
            link_end_pos: int = match.end() + position_shift
            line = line[:link_start_pos] + wrapped_link + line[link_end_pos:]
            position_shift += len(wrapped_link) - len(link)
        return line

    @staticmethod
    def _build_time_stamp() -> str:
        now = datetime.now()
        return now.astimezone().strftime('<span class="time" title="%Z (UTC%z)">%Y-%m-%d %H:%M:%S</span> ')
