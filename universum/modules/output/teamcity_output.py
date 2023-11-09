from .base_output import BaseOutput

__all__ = [
    "TeamcityOutput"
]


def escape(message: str) -> str:
    return message.replace('\r', '').replace('|', '||').replace('\'', '|\'').replace('[', '|[').replace(']', '|]')


class TeamcityOutput(BaseOutput):
    def log(self, line: str):
        print("==>", line)

    def log_error(self, description: str) -> None:
        lines = description.split("\n")
        for single_line in lines:
            print(f"##teamcity[message text='{escape(single_line)}' status='ERROR']")

    def log_external_command(self, command: str) -> None:
        print("$", command)

    def log_stdout(self, line: str) -> None:
        print(line)

    def log_stderr(self, line: str) -> None:
        lines = line.split("\n")
        for single_line in lines:
            print(f"##teamcity[message text='{escape(single_line)}' status='WARNING']")

    def open_block(self, num_str: str, name: str) -> None:
        print(f"##teamcity[blockOpened name='{num_str} {escape(name)}']")

    def close_block(self, num_str: str, name: str, status: str) -> None:
        print(f"##teamcity[blockClosed name='{num_str} {escape(name)}']")

    def log_skipped(self, message: str) -> None:
        lines = message.split("\n")
        for single_line in lines:
            print(f"##teamcity[message text='{escape(single_line)}' status='WARNING']")

    def log_summary_step(self, step_title: str, has_children: bool, status: str) -> None:
        if has_children:
            self.log(step_title)
        else:
            self.log(f"{step_title} - {status}")

    def report_build_problem(self, description: str) -> None:
        print(f"##teamcity[buildProblem description='<{escape(description)}>']")

    def set_build_status(self, status: str) -> None:
        print(f"##teamcity[buildStatus text='{escape(status)}']")
