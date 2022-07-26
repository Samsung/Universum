from __future__ import annotations

import contextlib
import copy

from typing import Callable, ClassVar, List, Optional, TypeVar, Union, Generator
from typing_extensions import TypedDict
from ..configuration_support import Step, Configuration
from ..lib.ci_exception import SilentAbortException, CriticalCiException
from ..lib.gravity import Dependency, Module
from .output import HasOutput

__all__ = [
    "HasStructure"
]


class Block:
    """
    >>> b1 = Block('Build for all supported platforms')
    >>> str(b1)
    ' Build for all supported platforms - Success'

    >>> b2 = Block('Build Android', b1)
    >>> str(b2)
    '1. Build Android - Success'

    >>> b3 = Block('Build Tizen', b1)
    >>> str(b3)
    '2. Build Tizen - Success'

    >>> b3.status = 'Failed'
    >>> str(b3)
    '2. Build Tizen - Failed'
    >>> b3.is_successful()
    False

    >>> b4 = Block('Run tests', b2)
    >>> str(b4)
    '1.1. Run tests - Success'
    >>> b4.is_successful()
    True
    >>> b2 is b4.parent
    True
    """

    def __init__(self, name: str, parent: Optional[Block] = None) -> None:
        self.name: str = name
        self.status: str = "Success"
        self.children: List[Block] = []

        self.parent: Optional[Block] = parent
        self.number: str = ''
        if parent:
            parent.children.append(self)
            self.number = f"{parent.number}{len(parent.children)}."

    def __str__(self) -> str:
        result = self.number + ' ' + self.name
        return f"{result} - {self.status}" if not self.children else result

    def is_successful(self) -> bool:
        return self.status == "Success"


class BackgroundStepInfo(TypedDict):
    name: str
    block: Block
    finalizer: Callable[[], None]
    artifacts_collection: Callable
    is_critical: bool


class StructureHandler(HasOutput):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_block: Optional[Block] = Block("Universum")
        self.configs_current_number: int = 0
        self.configs_total_count: int = 0
        self.active_background_steps: List[BackgroundStepInfo] = []
        self.step_num_len: int = 0
        self.group_numbering: str = ""

    def open_block(self, name: str) -> None:
        new_block = Block(name, self.current_block)
        self.current_block = new_block

        self.out.open_block(new_block.number, name)

    def close_block(self) -> None:
        if self.current_block is not None:
            block: Block = self.current_block
            self.current_block = self.current_block.parent
            self.out.close_block(block.number, block.name, block.status)

    def report_critical_block_failure(self) -> None:
        self.out.report_skipped("Critical step failed. All further configurations will be skipped")

    def report_skipped_block(self, name):
        new_skipped_block = Block(name, self.current_block)
        new_skipped_block.status = "Skipped"

        self.out.report_skipped(new_skipped_block.number + name + " skipped because of critical step failure")

    def fail_current_block(self, error: str = ""):
        block: Block = self.get_current_block()
        self.fail_block(block, error)

    def fail_block(self, block, error: str = ""):
        if error:
            self.out.log_exception(error)
        block.status = "Failed"
        self.out.report_build_problem(block.name + " " + block.status)

    def get_current_block(self):
        return self.current_block

    # The exact block will be reported as failed only if pass_errors is False
    # Otherwise the exception will be passed to the higher level function and handled there
    T = TypeVar('T')

    @contextlib.contextmanager
    def block(self, *, block_name: str, pass_errors: bool) -> Generator:
        self.open_block(block_name)
        try:
            yield
        except SilentAbortException:
            raise
        except CriticalCiException as e:
            self.fail_current_block(str(e))
            raise SilentAbortException() from e
        except Exception as e:
            if pass_errors is True:
                raise
            self.fail_current_block(str(e))
        finally:
            self.close_block()

    def execute_one_step(self, configuration: Step,
                         step_executor: Callable):
        # step_executor is [[Step], Step], but referring to Step creates circular dependency
        process = step_executor(configuration)

        error: Optional[str] = process.start()
        if error is not None:
            return process, error

        if not configuration.background:
            error = process.finalize()
            return process, error  # could be None or error message

        self.out.log("This step is marked to be executed in background")
        self.active_background_steps.append({'name': configuration.name,
                                             'block': self.get_current_block(),
                                             'finalizer': process.finalize,
                                             'artifacts_collection': process.collect_artifacts,
                                             'is_critical': configuration.critical})
        return process, None

    def finalize_background_step(self, background_step: BackgroundStepInfo):
        error = background_step['finalizer']()
        if error is not None:
            self.fail_block(background_step['block'], error)
            self.fail_current_block()
            return False

        return True

    def process_one_step(self, merged_item: Step, step_executor: Callable, skip_execution: bool) -> bool:
        """
        Process one step: either execute it or skip if the skip_execution flag is set.
        :param merged_item: Step to execute
        :param step_executor: Function that executes one step.
        :param skip_execution: If True, the step will be skipped, but reported to the output.
        :return: True if step was successfully executed, False otherwise. Skipping is considered success.
        """
        self.configs_current_number += 1
        numbering: str = f" [ {self.configs_current_number:>{self.step_num_len}}/{self.configs_total_count} ] "
        step_label: str = numbering + merged_item.name
        executed_successfully: bool = True

        if skip_execution:
            self.report_skipped_block(numbering + "'" + merged_item.name + "'")
            return executed_successfully

        # Here pass_errors=False, because any exception while executing build step
        # can be step-related and may not affect other steps
        process = None
        with self.block(block_name=step_label, pass_errors=False):
            process, error = self.execute_one_step(merged_item, step_executor)
            executed_successfully = (error is None)
            if not executed_successfully:
                self.fail_current_block(error)
        if not merged_item.background:
            with self.block(block_name=f"Collecting artifacts for the '{merged_item.name}' step", pass_errors=False):
                process.collect_artifacts()

        return executed_successfully

    def execute_steps_recursively(self, parent: Step,
                                  children: Configuration,
                                  step_executor: Callable,
                                  skip_execution: bool) -> bool:
        """
        :param parent: Parent step. Used for calculating actual attributes of child steps.
        :param children: Configuration object containing child steps.
        :param step_executor: Function that executes one step.
        :param skip_execution: If True, all steps will be skipped, but reported to the output.
        :return: True if all child steps were successful, False otherwise.
        """
        # step_executor is [[Step], Step], but referring to Step creates circular dependency

        some_step_failed: bool = False
        for child in children.configs:
            merged_item: Step = parent + child
            current_step_failed: bool
            if child.children:
                step_label: str = self.group_numbering + merged_item.name

                # Here pass_errors=True, because any exception outside executing build step
                # is not step-related and should stop script executing
                with self.block(block_name=step_label, pass_errors=True):
                    current_step_failed = not self.execute_steps_recursively(merged_item, child.children, step_executor,
                                                                             skip_execution)
            else:
                if merged_item.finish_background and self.active_background_steps:
                    self.out.log("All ongoing background steps should be finished before next step execution")
                    if not self.report_background_steps():
                        skip_execution = True

                current_step_failed = not self.process_one_step(merged_item, step_executor, skip_execution)

            if current_step_failed:
                some_step_failed = True

                if child.critical:
                    self.report_critical_block_failure()
                    skip_execution = True

        if some_step_failed:
            self.fail_current_block()

        return not some_step_failed

    def report_background_steps(self) -> bool:
        result: bool = True
        for item in self.active_background_steps:
            with self.block(block_name="Waiting for background step '" + item['name'] + "' to finish...",
                            pass_errors=True):
                if not self.finalize_background_step(item) and item['is_critical']:
                    result = False
                    self.out.report_skipped("The background step '" + item['name'] + "' failed, and as it is critical, "
                                            "all further steps will be skipped")
            with self.block(block_name=f"Collecting artifacts for the '{item['name']}' step", pass_errors=False):
                item['artifacts_collection']()

        self.out.log("All ongoing background steps completed")
        self.active_background_steps = []
        return result

    def execute_step_structure(self, configs: Configuration, step_executor) -> None:
        self.configs_total_count = sum(1 for _ in configs.all())
        self.step_num_len = len(str(self.configs_total_count))
        self.group_numbering = f" [ {'':{self.step_num_len}}+{'':{self.step_num_len}} ] "

        self.execute_steps_recursively(Step(), configs, step_executor, False)

        if self.active_background_steps:
            with self.block(block_name="Reporting background steps", pass_errors=False):
                self.report_background_steps()


class HasStructure(Module):
    structure_factory: ClassVar = Dependency(StructureHandler)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.structure: StructureHandler = self.structure_factory()
