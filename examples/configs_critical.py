#!/usr/bin/env python

from universum.configuration_support import Configuration

not_script = Configuration([dict(name='Not script', command=["not_run.sh"], critical=True)])

script = Configuration([dict(command=["run.sh"])])

step = Configuration([dict(name='Step 1', critical=True), dict(name='Step 2')])

substep = Configuration([dict(name=', failed substep', command=["fail"]),
                         dict(name=', successful substep', command=["pass"])])

configs = script * step * substep + not_script + script


if __name__ == '__main__':
    print(configs.dump())
