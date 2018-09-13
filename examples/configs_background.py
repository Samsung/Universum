#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from _universum.configuration_support import Variations

background = Variations([dict(name="Background", background=True)])
sleep = Variations([dict(name=' long step', command=["sleep", "1"])])
multiply = Variations([dict(name="_1"), dict(name="_2"), dict(name="_3")])
wait = Variations([dict(name='Step requiring background results',
                        command=["run.sh", "pass"], finish_background=True)])

script = Variations([dict(name=" unsuccessful step", command=["run.sh", "fail"])])

configs = background * (script + sleep * multiply) + wait + background * (sleep + script)


if __name__ == '__main__':
    print configs.dump()