from ...lib.gravity import Module


class BaseOutput(Module):
    """
    Abstract base class for output drivers
    """

    def log_execution_start(self, title: str, version: str) -> None:
        self.log(self._build_execution_start_msg(title, version))

    def log_execution_finish(self, title: str, version: str) -> None:
        self.log(self._build_execution_finish_msg(title, version))

    def log(self, line: str) -> None:
        raise NotImplementedError

    def log_error(self, description: str) -> None:
        raise NotImplementedError

    def log_external_command(self, command: str) -> None:
        raise NotImplementedError

    def log_stdout(self, line: str) -> None:
        raise NotImplementedError

    def log_stderr(self, line: str) -> None:
        raise NotImplementedError

    def open_block(self, num_str: str, name: str) -> None:
        raise NotImplementedError

    def close_block(self, num_str: str, name: str, status: str) -> None:
        raise NotImplementedError

    def log_skipped(self, message: str) -> None:
        raise NotImplementedError

    def log_summary_step(self, step_title: str, has_children: bool, status: str) -> None:
        raise NotImplementedError

    def report_build_problem(self, description: str) -> None:
        raise NotImplementedError

    def set_build_title(self, message: str) -> None:
        raise NotImplementedError

    @staticmethod
    def _build_execution_start_msg(title: str, version: str) -> str:
        return f"{title} {version} started execution"

    @staticmethod
    def _build_execution_finish_msg(title: str, version: str) -> str:
        return f"{title} {version} finished execution"
