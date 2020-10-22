#!/usr/bin/env python

from universum.configuration_support import Configuration, Step

not_script = Configuration([Step(name='Not script', command=["not_run.sh"], critical=True)])

script = Configuration([Step(command=["run.sh"])])

step = Configuration([Step(name='Step 1', critical=True), Step(name='Step 2')])

substep = Configuration([Step(name=', failed substep', command=["fail"]),
                         Step(name=', successful substep', command=["pass"])])

configs = script * step * substep + not_script + script


if __name__ == '__main__':
    print(configs.dump())
