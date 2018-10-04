#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from _universum.configuration_support import Variations

not_script = Variations([dict(name='Not script', command=["not_run.sh"], critical=True)])

script = Variations([dict(command=["run.sh"])])

step = Variations([dict(name='Step 1', critical=True), dict(name='Step 2')])

substep = Variations([dict(name=', failed substep', command=["fail"]),
                      dict(name=', successful substep', command=["pass"])])

configs = script * step * substep + not_script + script


if __name__ == '__main__':
    print configs.dump()
