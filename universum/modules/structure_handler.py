import copy

from typing import Callable, ClassVar, List, Optional, TypeVar
from .. import configuration_support
from ..lib.ci_exception import SilentAbortException, StepException, CriticalCiException
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

    def __init__(self, name: str, parent: Optional['Block'] = None) -> None:
        self.name: str = name
        self.status: str = "Success"
        self.children: List[Block] = []

        self.parent: Optional[Block] = parent
        self.number: str = ''
        if parent:
            parent.children.append(self)
            self.number = '{}{}.'.format(parent.number, len(parent.children))

    def __str__(self) -> str:
        result = self.number + ' ' + self.name
        return '{} - {}'.format(result, self.status) if not self.children else result

    def is_successful(self) -> bool:
        return self.status == "Success"


class StructureHandler(HasOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_block: Optional[Block] = Block("Universum")
        self.configs_current_number: int = 0
        self.configs_total_count: int = 0
        self.active_background_steps = []
        # noinspection PyUnresolvedReferences
        self.out: 'Output'  # TODO: add annotations in ./universum/module/output/output.py for @needs_output

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

    def run_in_block(self, operation: Callable[..., T],
                     block_name: str, pass_errors: bool, *args, **kwargs) -> Optional[T]:
        result = None
        self.open_block(block_name)
        try:
            result = operation(*args, **kwargs)
        except (SilentAbortException, StepException):
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
        return result

    def execute_one_step(self, configuration, executor, is_critical):
        process = executor(configuration)

        background = configuration.get("background", False)
        process.start(is_background=background)
        if not background:
            process.finalize()
            return

        self.out.log("Will continue in background")
        self.active_background_steps.append({'name': configuration.get("name", ""),
                                             'finalizer': process.finalize,
                                             'is_critical': is_critical})

    def finalize_background_step(self, step):
        try:
            step['finalizer']()
            self.out.log("This background step finished successfully")
        except StepException:
            if step['is_critical']:
                self.out.log_stderr("This background step failed, and as it was critical, "
                                    "all further steps will be skipped")
                return False
            self.out.log_stderr("This background step failed")
        return True

    def execute_steps_recursively(self, parent, variations, step_executor, skipped=False):
        if parent is None:
            parent = dict()

        step_num_len = len(str(self.configs_total_count))
        child_step_failed = False
        for obj_a in variations:
            try:
                item = configuration_support.combine(parent, copy.deepcopy(obj_a))

                if "children" in obj_a:
                    # Here pass_errors=True, because any exception outside executing build step
                    # is not step-related and should stop script executing

                    numbering = " [ {:{length}}+{:{length}} ] ".format("", "", length=step_num_len)
                    step_name = numbering + item.get("name", ' ')
                    self.run_in_block(self.execute_steps_recursively, step_name, True,
                                      item, obj_a["children"], step_executor, skipped)
                else:
                    self.configs_current_number += 1
                    numbering = " [ {:>{}}/{} ] ".format(
                        self.configs_current_number,
                        step_num_len,
                        self.configs_total_count
                    )
                    step_name = numbering + item.get("name", ' ')
                    if skipped:
                        self.report_skipped_block(step_name)
                        continue

                    if item.get("finish_background", False) and self.active_background_steps:
                        self.out.log("All ongoing background steps should be finished before next step execution")
                        if not self.report_background_steps():
                            self.report_skipped_block(step_name)
                            skipped = True
                            raise StepException()

                    # Here pass_errors=False, because any exception while executing build step
                    # can be step-related and may not affect other steps
                    self.run_in_block(self.execute_one_step, step_name, False,
                                      item, step_executor, obj_a.get("critical", False))
            except StepException:
                child_step_failed = True
                if obj_a.get("critical", False):
                    self.report_critical_block_failure()
                    skipped = True
        if child_step_failed:
            raise StepException()

    def report_background_steps(self):
        result = True
        for item in self.active_background_steps:
            if not self.run_in_block(self.finalize_background_step,
                                     "Waiting for background step '" + item['name'] + "' to finish...",
                                     True, item):
                result = False
        self.out.log("All ongoing background steps completed")
        self.active_background_steps = []
        return result

    def execute_step_structure(self, configs, step_executor):
        self.configs_total_count = sum(1 for _ in configs.all())

        try:
            self.execute_steps_recursively(None, configs, step_executor)
        except StepException:
            pass

        if self.active_background_steps:
            self.run_in_block(self.report_background_steps, "Reporting background steps", False)


class HasStructure(Module):
    structure_factory: ClassVar = Dependency(StructureHandler)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.structure: StructureHandler = self.structure_factory()
