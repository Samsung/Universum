#!/usr/bin/env python

from universum.configuration_support import Configuration, Step

configs = Configuration([Step(name='Build ', command=['build.sh'], artifacts='out')])

if __name__ == '__main__':
    print(configs.dump())
