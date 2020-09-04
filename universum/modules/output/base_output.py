from ...lib.gravity import Module


class BaseOutput(Module):
    """
    Abstract base class for output drivers
    """

    def open_block(self, num_str, name):
        raise NotImplementedError

    def close_block(self, num_str, name, status):
        raise NotImplementedError

    def report_error(self, description):
        raise NotImplementedError

    def report_skipped(self, message):
        raise NotImplementedError

    def report_step(self, message, status):
        self.log(message)

    def change_status(self, message):
        raise NotImplementedError

    def log_exception(self, line):
        raise NotImplementedError

    def log_stderr(self, line):
        raise NotImplementedError

    def log(self, line):
        raise NotImplementedError

    def log_external_command(self, command):
        raise NotImplementedError

    def log_shell_output(self, line):
        raise NotImplementedError
