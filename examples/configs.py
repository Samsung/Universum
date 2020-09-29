#!/usr/bin/env python

from universum.configuration_support import Variations

not_script = Variations([dict(name='Not script', command=["not_run.sh"])])

script = Variations([dict(command=["run.sh"], directory="examples")])

step = Variations([dict(name='Step 1', critical=True), dict(name='Step 2')])

additional_substep = Variations([dict(name=', additional substep', command=["fail"], critical=False)])

substep = Variations([dict(name=', failed substep', command=["fail"], artrifacts="*.sh"),
                      dict(name=', successful substep', command=["pass"], artifacts="*.txt")])

configs = not_script + script * step * (substep + additional_substep)

if __name__ == '__main__':
    print(configs.dump())
