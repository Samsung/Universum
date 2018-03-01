# -*- coding: UTF-8 -*-

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
    def __init__(self, name):
        self.name = name
        self.status = "Success"
        self.child_number = 1


@needs_output
class StructureHandler(Module):
    def __init__(self):
        self.top_block_number = 1
        self.blocks = []

    def get_block_num_str(self):
        num_str = unicode(self.top_block_number) + "."
        for block in self.blocks:
            num_str += unicode(block.child_number) + "."
        return num_str

    def open_block(self, name):
        self.out.open_block(self.get_block_num_str(), name)
        self.blocks.append(Block(name))

    def close_block(self):
        block = self.blocks.pop()
        if block.status == "Failed":
            self.out.report_build_problem(block.name + " " + block.status)

        self.out.close_block(self.get_block_num_str(), block.name, block.status)

        if not self.blocks:
            self.top_block_number += 1
        else:
            self.blocks[-1].child_number += 1

    def report_critical_block_failure(self):
        self.out.report_skipped("Critical step failed. All further configurations will be skipped")

    def report_skipped_block(self, name):
        self.out.report_skipped(self.get_block_num_str() + " " + name + " skipped because of critical step failure")
        if not self.blocks:
            self.top_block_number += 1
        else:
            self.blocks[-1].child_number += 1

    def fail_current_block(self, error=None):
        if error:
            self.out.log_exception(error)
        self.blocks[-1].status = "Failed"

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
