#!/usr/bin/env python

from universum.configuration_support import Configuration, Step

script_name = './basic_build_script.sh'

build = Configuration([Step(name='Build ', command=[script_name], artifacts='out')])

platforms = Configuration([Step(name='for platform A ', command=['--platform_a'], if_env_set="PLATFORM == A"),
                           Step(name='for platform B ', command=['--platform_b'], if_env_set="PLATFORM == B")])

bits = Configuration([Step(name='32 bits', command=['--32'], artifacts='/result*32.txt'),
                      Step(name='64 bits', command=['--64'], if_env_set=" & IS_X64")])

# Will run every platform with a specified tool with '--32' flag
# Will run same platforms with '--64' flag only if $IS_X64 variable is set (e.g. by "export IS_X64=true")
configs = build * platforms * bits


if __name__ == '__main__':
    print(configs.dump())
