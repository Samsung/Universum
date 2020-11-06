#!/usr/bin/env python

from universum.configuration_support import Configuration, Step

background = Configuration([Step(name="Background", background=True)])
sleep = Configuration([Step(name=' long step', command=["sleep", "1"])])
multiply = Configuration([Step(name="_1"), Step(name="_2"), Step(name="_3")])
wait = Configuration([Step(name='Step requiring background results',
                           command=["run.sh", "pass"], finish_background=True)])

script = Configuration([Step(name=" unsuccessful step", command=["run.sh", "fail"])])

configs = background * (script + sleep * multiply) + wait + background * (sleep + script)


if __name__ == '__main__':
    print(configs.dump())