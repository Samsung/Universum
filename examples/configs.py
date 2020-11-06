#!/usr/bin/env python

from universum.configuration_support import Configuration, Step

not_script = Configuration([Step(name='Not script', command=["not_run.sh"])])

script = Configuration([Step(command=["run.sh"], directory="examples")])

step = Configuration([Step(name='Step 1', critical=True), Step(name='Step 2')])

additional_substep = Configuration([Step(name=', additional substep', command=["fail"], critical=False)])

substep = Configuration([Step(name=', failed substep', command=["fail"], artrifacts="*.sh"),
                         Step(name=', successful substep', command=["pass"], artifacts="*.txt")])

configs = not_script + script * step * (substep + additional_substep)

if __name__ == '__main__':
    print(configs.dump())
