#!/usr/bin/env python

import os.path
from universum.configuration_support import Variations, get_project_root

#
# One way to specify path to the script: add full path to the command
#
script_name = './basic_build_script.sh'
script_path = os.path.abspath(os.path.join(get_project_root(), script_name))

build32 = Variations([dict(name='Build ', command=[script_path], artifacts='out')])

platforms32 = Variations([dict(name='for platform A ', command=['--platform_a']),
                          dict(name='for platform B ', command=['--platform_b'])])

bits32 = Variations([dict(name='32 bits', command=['--32'], artifacts='/result*32.txt')])
configs = build32 * platforms32 * bits32


#
# Alternative way to specify path to the script: provide working directory in the 'directory' attribute of configuration
#
build64 = Variations([dict(name='Build ', directory=get_project_root(), command=[script_name], artifacts='out')])
platforms64 = Variations([dict(name='for platform C ', command=['--platform_c'])])
bits64 = Variations([dict(name='64 bits', command=['--64'])])
configs += build64 * (platforms32 + platforms64) * bits64

if __name__ == '__main__':
    print(configs.dump())
