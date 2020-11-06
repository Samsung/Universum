from universum.configuration_support import Configuration


one = Configuration([{'name': 'one', 'command': ['echo', 'one']}])

two = Configuration([{'name': 'two'}])
two_one = Configuration([{'name': '_one', 'command': ['./universum_config/sleep_and_fail.sh']}])
two_two = Configuration([{'name': '_two', 'command': ['./universum_config/large_output_and_success.sh']}])

three = Configuration([{'name': 'three', 'command': ['./universum_config/fail.sh']}])

configs = one + two * (two_one + two_two) + three
