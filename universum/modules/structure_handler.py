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
    is_critical: bool


class StructureHandler(HasOutput):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_block: Optional[Block] = Block("Universum")
        self.configs_current_number: int = 0
        self.configs_total_count: int = 0
        self.active_background_steps: List[BackgroundStepInfo] = []

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

        # TODO: wrap block name in quotes
        self.out.report_skipped(new_skipped_block.number + " " + name +
                                " skipped because of critical step failure")

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

    def run_in_block(self, operation: Callable[..., T],
                     block_name: str, pass_errors: bool, *args, **kwargs) -> Optional[T]:
        with self.block(block_name=block_name, pass_errors=pass_errors):
            return operation(*args, **kwargs)

    def execute_one_step(self, configuration: Step,
                         step_executor: Callable, is_critical: bool) -> Optional[str]:
        # step_executor is [[Step], Step], but referring to Step creates circular dependency
        process = step_executor(configuration)

        error: Optional[str] = process.start()
        if error is not None:
            return error

        if not configuration.background:
            error = process.finalize()
            return error  # could be None or error message

        self.out.log("This step is marked to be executed in background")
        self.active_background_steps.append({'name': configuration.name,
                                             'block': self.get_current_block(),
                                             'finalizer': process.finalize,
                                             'is_critical': is_critical})
        return None

    def finalize_background_step(self, background_step: BackgroundStepInfo):
        error = background_step['finalizer']()
        if error is not None:
            self.fail_block(background_step['block'], error)
            self.fail_current_block()
            return False

        return True

    def execute_steps_recursively(self, parent: Step, cfg: Configuration,
                                  step_executor: Callable,
                                  skip_execution: bool = False) -> Optional[str]:
        """

        :param parent: Parent step. Used for calculating actual attributes of child steps.
        :param cfg: List of steps to execute.
        :param step_executor: Function that executes one step.
        :param skip_execution: If True, all steps will be skipped, but reported to the output.
        :return: True if any child step failed, False otherwise.
        """
        # step_executor is [[Step], Step], but referring to Step creates circular dependency

        step_num_len = len(str(self.configs_total_count))
        error: Optional[str]
        child_step_error: Optional[str] = None
        for obj_a in cfg.configs:
            item: Step = parent + copy.deepcopy(obj_a)

            if obj_a.children:

                numbering = f" [ {'':{step_num_len}}+{'':{step_num_len}} ] "
                step_name = numbering + item.name

                # Here pass_errors=True, because any exception outside executing build step
                # is not step-related and should stop script executing
                with self.block(block_name=step_name, pass_errors=True):
                    error = self.execute_steps_recursively(item, obj_a.children, step_executor, skip_execution)
                    if error is not None:
                        self.fail_current_block()
            else:
                if item.finish_background and self.active_background_steps:
                    self.out.log("All ongoing background steps should be finished before next step execution")
                    if not self.report_background_steps():
                        skip_execution = True

                self.configs_current_number += 1
                numbering = f" [ {self.configs_current_number:>{step_num_len}}/{self.configs_total_count} ] "
                step_name = numbering + item.name

                if skip_execution:
                    self.report_skipped_block(step_name)
                    continue

                # Here pass_errors=False, because any exception while executing build step
                # can be step-related and may not affect other steps
                with self.block(block_name=step_name, pass_errors=False):
                    error = self.execute_one_step(item, step_executor, obj_a.critical)
                    if error is not None:
                        self.fail_current_block(error)

            if error is not None:
                child_step_error = ""  # Indicate that child step failed, but forget the error message

                if obj_a.critical:
                    self.report_critical_block_failure()
                    skip_execution = True

        return child_step_error

    def report_background_steps(self) -> bool:
        result = True
        for item in self.active_background_steps:
            if self.run_in_block(self.finalize_background_step,
                                 "Waiting for background step '" + item['name'] + "' to finish...",
                                 True, item):
                continue

            if item['is_critical']:
                result = False
                self.out.report_skipped("The background step '" + item['name'] + "' failed, and as it is critical, "
                                        "all further steps will be skipped")

        self.out.log("All ongoing background steps completed")
        self.active_background_steps = []
        return result

    def execute_step_structure(self, configs: Configuration, step_executor) -> None:
        self.configs_total_count = sum(1 for _ in configs.all())

        self.execute_steps_recursively(Step(), configs, step_executor)

        if self.active_background_steps:
            self.run_in_block(self.report_background_steps, "Reporting background steps", False)


class HasStructure(Module):
    structure_factory: ClassVar = Dependency(StructureHandler)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.structure: StructureHandler = self.structure_factory()
