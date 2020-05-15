#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function
from universum.configuration_support import Variations

configs = Variations([dict(name='Build ', command=['build.sh'], artifacts='out')])

if __name__ == '__main__':
    print(configs.dump())
