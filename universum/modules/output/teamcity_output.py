from .base_output import BaseOutput

__all__ = [
    "TeamcityOutput"
]


def escape(message):
    return message.replace('\r', '').replace('|', '||').replace('\'', '|\'').replace('[', '|[').replace(']', '|]')


class TeamcityOutput(BaseOutput):
    def log(self, line):
        print("==>", line)

    def log_error(self, description):
        lines = description.split("\n")
        for single_line in lines:
            print(f"##teamcity[message text='{escape(single_line)}' status='ERROR']")

    def log_external_command(self, command):
        print("$", command)

    def log_stdout(self, line):
        print(line)

    def log_stderr(self, line):
        lines = line.split("\n")
        for single_line in lines:
            print(f"##teamcity[message text='{escape(single_line)}' status='WARNING']")

    def open_block(self, num_str, name):
        print(f"##teamcity[blockOpened name='{num_str} {escape(name)}']")

    def close_block(self, num_str, name, status):
        print(f"##teamcity[block\\Closed name='{num_str} {escape(name)}']")

    def log_skipped(self, message):
        lines = message.split("\n")
        for single_line in lines:
            print(f"##teamcity[message text='{escape(single_line)}' status='WARNING']")

    def log_summary_step(self, step_title, has_children, status):
        if has_children:
            self.log(step_title)
        else:
            self.log(f"{step_title} - {status}")

    def report_build_problem(self, description):
        print(f"##teamcity[buildProblem description='<{escape(description)}>']")

    def set_build_title(self, message):
        print(f"##teamcity[buildStatus text='{escape(message)}']")
