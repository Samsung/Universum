#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from universum.configuration_support import Variations

configs = Variations([dict(name='Build ', command=['build.sh'], artifacts='out')])

if __name__ == '__main__':
    print(configs.dump())
