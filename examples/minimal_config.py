#!/usr/bin/env python3.7

from universum.configuration_support import Variations

configs = Variations([dict(name='Build ', command=['build.sh'], artifacts='out')])

if __name__ == '__main__':
    print(configs.dump())
