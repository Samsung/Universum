from universum.configuration_support import Variations


one = Variations([{'name': 'one', 'command': ['echo', 'one']}])

two = Variations([{'name': 'two'}])
two_one = Variations([{'name': '_one', 'command': ['./universum_config/sleep_and_fail.sh']}])
two_two = Variations([{'name': '_two', 'command': ['./universum_config/large_output_and_success.sh']}])

three = Variations([{'name': 'three', 'command': ['./universum_config/fail.sh']}])

configs = one + two * (two_one + two_two) + three
