from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from typing import Callable, ClassVar, List, Optional, TypeVar, Generator

from typing_extensions import TypedDict

from .output import HasOutput
from ..configuration_support import Step, Configuration
from ..lib.ci_exception import SilentAbortException, CriticalCiException
from ..lib.gravity import Dependency, Module

__all__ = [
    "HasStructure",
    "Block",
    "RunningStepBase"
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
    process: RunningStepBase
    is_critical: bool
    has_artifacts: bool


class RunningStepBase(ABC):

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def finalize(self) -> None:
        pass

    @abstractmethod
    def get_error(self) -> Optional[str]:
        pass

    @abstractmethod
    def collect_artifacts(self) -> None:
        pass


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

    def log_critical_block_failure(self) -> None:
        self.out.log_skipped("Critical step failed. All further configurations will be skipped")

    def log_skipped_block(self, name):
        new_skipped_block = Block(name, self.current_block)
        new_skipped_block.status = "Skipped"

        self.out.log_skipped(new_skipped_block.number + name + " skipped because of critical step failure")

    def fail_current_block(self, error: str = ""):
        block: Block = self.get_current_block()
        self.fail_block(block, error)

    def fail_block(self, block, error: str = ""):
        if error:
            self.out.log_error(error)
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
        except CriticalCiException as e:  # system/environment step failed
            self.fail_current_block(str(e))
            raise SilentAbortException() from e
        except Exception as e:  # unexpected failure, should not occur
            if pass_errors is True:
                raise
            self.fail_current_block(str(e))
        finally:
            self.close_block()

    def execute_one_step(self, configuration: Step,
                         step_executor: Callable[[Step], RunningStepBase]) -> RunningStepBase:
        process: RunningStepBase = step_executor(configuration)
        process.start()
        if process.get_error() is not None:
            return process
        if not configuration.background:
            process.finalize()
            return process
        self.out.log("This step is marked to be executed in background")
        has_artifacts: bool = bool(configuration.artifacts) or bool(configuration.report_artifacts)
        self.active_background_steps.append({'name': configuration.name,
                                             'block': self.get_current_block(),
                                             'process': process,
                                             'is_critical': configuration.critical,
                                             'has_artifacts': has_artifacts})
        return process

    def finalize_background_step(self, background_step: BackgroundStepInfo) -> bool:
        process: RunningStepBase = background_step['process']
        process.finalize()
        error: Optional[str] = process.get_error()
        if error is not None:
            self.fail_block(background_step['block'], error)
            self.fail_current_block()
            return False

        return True

    def process_one_step(self, merged_item: Step, step_executor: Callable, skip_execution: bool) -> bool:
        """
        Process one step: either execute it or skip if the skip_execution flag is set.
        :param merged_item: Step to execute.
        :param step_executor: Function that executes one step.
        :param skip_execution: If True, the step will be skipped, but reported to the output.
        :return: True if step was successfully executed, False otherwise. Skipping is considered success.
        """
        self.configs_current_number += 1
        numbering: str = f" [ {self.configs_current_number:>{self.step_num_len}}/{self.configs_total_count} ] "
        step_label: str = numbering + merged_item.name

        if skip_execution:
            self.log_skipped_block(numbering + "'" + merged_item.name + "'")
            return True

        process: Optional[RunningStepBase] = None
        error: Optional[str] = None
        # Here pass_errors=False, because any exception while executing build step
        # can be step-related and may not affect other steps
        with self.block(block_name=step_label, pass_errors=False):
            process = self.execute_one_step(merged_item, step_executor)
            error = process.get_error()
            if error and not merged_item.is_conditional:
                self.fail_current_block(error)
        has_artifacts: bool = bool(merged_item.artifacts) or bool(merged_item.report_artifacts)
        if not merged_item.background and has_artifacts:
            with self.block(block_name=f"Collecting artifacts for the '{merged_item.name}' step", pass_errors=False):
                process.collect_artifacts()

        return error is None

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
            elif child.is_conditional:
                conditional_step_succeeded: bool = self.process_one_step(merged_item, step_executor,
                                                                         skip_execution=False)
                step_to_execute: Optional[Configuration] = merged_item.if_succeeded if conditional_step_succeeded \
                    else merged_item.if_failed
                if step_to_execute:  # branch step can be not set
                    self.execute_steps_recursively(parent=Step(),
                                                   children=step_to_execute,
                                                   step_executor=step_executor,
                                                   skip_execution=False)
                current_step_failed = False  # conditional step should be always successful
            else:
                if merged_item.finish_background and self.active_background_steps:
                    self.out.log("All ongoing background steps should be finished before next step execution")
                    if not self.report_background_steps():
                        skip_execution = True
                current_step_failed = not self.process_one_step(merged_item, step_executor, skip_execution)

            if current_step_failed:
                some_step_failed = True

                if child.critical:
                    self.log_critical_block_failure()
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
                    self.out.log_skipped("The background step '" + item['name'] + "' failed, and as it is critical, "
                                                                                  "all further steps will be skipped")
            if item['has_artifacts']:
                with self.block(block_name=f"Collecting artifacts for the '{item['name']}' step", pass_errors=False):
                    item['process'].collect_artifacts()

        self.out.log("All ongoing background steps completed")
        self.active_background_steps = []
        return result

    def execute_step_structure(self, configs: Configuration, step_executor) -> None:
        for config in configs.all():
            self.configs_total_count += 1
            if config.is_conditional:
                self.configs_total_count += 1
        self.step_num_len = len(str(self.configs_total_count))
        self.group_numbering = f" [ {'':{self.step_num_len}}+{'':{self.step_num_len}} ] "

        self.execute_steps_recursively(Step(), configs, step_executor, False)

        if self.active_background_steps:
            with self.block(block_name="Reporting background steps", pass_errors=False):
                self.report_background_steps()

    def _build_step_name(self, name):
        step_num_len = len(str(self.configs_total_count))
        numbering = f" [ {self.configs_current_number:>{step_num_len}}/{self.configs_total_count} ] "
        return numbering + name


class HasStructure(Module):
    structure_factory: ClassVar = Dependency(StructureHandler)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.structure: StructureHandler = self.structure_factory()
