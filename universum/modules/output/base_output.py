from ...lib.gravity import Module


class BaseOutput(Module):
    """
    Abstract base class for output drivers.  Defines methods that have to be implemented by each module that
    implements a type of output.
    """

    def log_execution_start(self, title: str, version: str) -> None:
        """
        Print the universum startup message, for example:
        "==> Universum xx.yy.zz started execution"

        :param title: name of the product
        :param version: version of the product
        """
        self.log(self._build_execution_start_msg(title, version))

    def log_execution_finish(self, title: str, version: str) -> None:
        """
        Print the universum finished message, for example:
        "==> Universum xx.yy.zz finished execution"

        :param title: name of the product
        :param version: version of the product
        """
        self.log(self._build_execution_finish_msg(title, version))

    def log(self, line: str) -> None:
        """
        Print a line to the output. The most generic type of log.
        Mostly used for printing own messages of universum.

        :param line: the line to print
        """
        raise NotImplementedError

    def log_error(self, description: str) -> None:
        """
        Print an error message to the output. Error may use different colors or other formatting.
        Used for printing own error messages of the universum as well as error messages from other modules and libraries
        and operating system.

        :param description: the detailed error message
        """
        raise NotImplementedError

    def log_external_command(self, command: str) -> None:
        """
        Print the start of the launch of the external command. Full command line with all arameters is supposed to be
        printed.

        :param command: external command with parameters
        """
        raise NotImplementedError

    def log_stdout(self, line: str) -> None:
        """
        Print one line of the standard output of the previously launched external command. The only usage is for
        printing output of the commands that are launched during the execution of the universum config.

        :param line: the line to print
        """
        raise NotImplementedError

    def log_stderr(self, line: str) -> None:
        """
        Print one line of the standard error output of the previously launched external command. The only usage is for
        printing standard error output of the commands that are launched during the execution of the universum config.

        :param line: the line to print
        """
        raise NotImplementedError

    def open_block(self, num_str: str, name: str) -> None:
        """
        Start the block of the output. Block is a group of related output lines.
        Depending on the capabilities of the output, the blocks can be marked by indentation, color or numbering.
        Output can also implement dynamic blocks collapsing and expanding.

        :param num_str: the string that represents the block number within the hierarchy.
            Inner blocks are numbered using dot notation.
            The number string is passed as a separate parameter to allow implementing different formatting for number and
            name.
        :param name: the title of the block.
        """
        raise NotImplementedError

    def close_block(self, num_str: str, name: str, status: str) -> None:
        """
        End the block of the output.

        :param num_str: the string that represents the block number
        :param name: the title of the block
        :param status: the completion status of the block: "Passed" or "Failed"
        """
        raise NotImplementedError

    def log_skipped(self, message: str) -> None:
        """
        Print a message related to skipping steps. It could be a warning that further steps are skipped, or a message
        that the step is skipped.

        :param message: the message to print
        """
        raise NotImplementedError

    def log_summary_step(self, step_title: str, has_children: bool, status: str) -> None:
        """
        Print a summary of the step execution at the end of the run.

        :param step_title: the title of the step
        :param has_children: whether the step has children or not. Typically, if step has children, the status is not
            included in the summary.
        :param status: the status of the step: "Passed", "Failed" or "Skipped"
        """
        raise NotImplementedError

    def report_build_problem(self, description: str) -> None:
        """
        TeamCity only. Report run problem to the TeamCity via the output. Also fails the build regardless of the process
        exit code. Multiple build problems for single run can be reported.

        :param description: the description of the problem
        """
        raise NotImplementedError

    def set_build_status(self, status: str) -> None:
        """
        TeamCity only. Set the title of the build. Changes the status of the build visible in the configuration build
        history and on the build page itself. For builds containing build problems, by default the status is
        automatically populated with them by the TeamCity server itself. This method allows to override the status.

        :param status: the status (title) of the build
        """
        raise NotImplementedError

    @staticmethod
    def _build_execution_start_msg(title: str, version: str) -> str:
        return f"{title} {version} started execution"

    @staticmethod
    def _build_execution_finish_msg(title: str, version: str) -> str:
        return f"{title} {version} finished execution"
