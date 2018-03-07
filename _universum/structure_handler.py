# -*- coding: UTF-8 -*-
import copy

from . import configuration_support
from .ci_exception import SilentAbortException, StepException, CriticalCiException
from .gravity import Module, Dependency
from .output import needs_output

__all__ = [
    "StructureHandler",
    "needs_structure"
]


def needs_structure(klass):
    klass.structure_factory = Dependency("StructureHandler")
    original_init = klass.__init__

    def new_init(self, *args, **kwargs):
        self.structure = self.structure_factory()
        original_init(self, *args, **kwargs)

    klass.__init__ = new_init
    return klass


class Block(object):
    def __init__(self, name, parent=None):
        self.name = name
        self.status = "Success"
        if parent:
            self.number = len(parent.children) + 1
        else:
            self.number = 0
        self.children = []
        self.parent = parent

    def set_status(self, status):
        self.status = status

    def get_status(self):
        return self.status

    def get_full_status(self):
        text = get_block_num_str(self) + " "
        if self.children:
            text += self.name
        else:
            text += self.name + " - " + self.status
        if self.status == "Success":
            return text, True
        return text, False


def get_block_num_str(block):
    num_str = ""
    while block.parent:
        num_str = str(block.number) + "." + num_str
        block = block.parent
    return num_str


@needs_output
class StructureHandler(Module):
    def __init__(self):
        block_structure = Block("Universum")
        self.current_block = block_structure
        self.configs_current_number = 0
        self.configs_total_count = 0

    def open_block(self, name):
        new_block = Block(name, self.current_block)
        self.current_block.children.append(new_block)
        self.current_block = new_block

        self.out.open_block(get_block_num_str(new_block), name)

    def close_block(self):
        block = self.current_block
        self.current_block = self.current_block.parent

        if block.get_status() == "Failed":
            self.out.report_build_problem(block.name + " " + block.status)

        self.out.close_block(get_block_num_str(block), block.name, block.status)

    def report_critical_block_failure(self):
        self.out.report_skipped("Critical step failed. All further configurations will be skipped")

    def report_skipped_block(self, name):
        new_skipped_block = Block(name, self.current_block)
        new_skipped_block.set_status("Skipped")
        self.current_block.children.append(new_skipped_block)

        self.out.report_skipped(get_block_num_str(new_skipped_block) + " " + name +
                                " skipped because of critical step failure")

    def fail_current_block(self, error=None):
        if error:
            self.out.log_exception(error)
        self.current_block.set_status("Failed")

    def get_current_block(self):
        return self.current_block

    # The exact block will be reported as failed only if pass_errors is False
    # Otherwise the exception will be passed to the higher level function and handled there
    def run_in_block(self, operation, block_name, pass_errors, *args, **kwargs):
        result = None
        self.open_block(block_name)
        try:
            result = operation(*args, **kwargs)
        except (SilentAbortException, StepException):
            raise
        except CriticalCiException as e:
            self.fail_current_block(unicode(e))
            raise SilentAbortException()
        except Exception as e:
            if pass_errors is True:
                raise
            else:
                self.fail_current_block(unicode(e))
        finally:
            self.close_block()
        return result

    def execute_step_structure(self, configs, step_executor):
        self.configs_total_count = sum(1 for _ in configs.all())
        self.execute_steps_recursively(None, configs, step_executor)

    def execute_steps_recursively(self, parent, variations, step_executor, skipped=False):
        if parent is None:
            parent = dict()

        child_step_failed = False
        for obj_a in variations:
            try:
                item = configuration_support.combine(parent, copy.deepcopy(obj_a))

                if "children" in obj_a:
                    # Here pass_errors=True, because any exception outside executing build step
                    # is not step-related and should stop script executing

                    self.run_in_block(self.execute_steps_recursively, item.get("name", ' '), True,
                                      item, obj_a["children"], step_executor, skipped)
                else:
                    self.configs_current_number += 1
                    step_name = " [ " + unicode(self.configs_current_number) + "/" + \
                                unicode(self.configs_total_count) + " ] " + item.get("name", ' ')
                    # Here pass_errors=False, because any exception while executing build step
                    # can be step-related and may not affect other steps

                    if not skipped:
                        self.run_in_block(step_executor, step_name, False, item)
                    else:
                        self.report_skipped_block(step_name)
            except StepException:
                child_step_failed = True
                if obj_a.get("critical", False):
                    self.report_critical_block_failure()
                    skipped = True
        if child_step_failed:
            raise StepException
