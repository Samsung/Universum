#!/bin/bash

rm -rf /tmp/pytest-of-user/* ; env -i PATH=$PATH pytest -vvs >> clear_launch.log 2>&1
rm -rf /tmp/pytest-of-user/* ; env -i PATH=$PATH JENKINS_HOME=1 BUILD_URL=1 pytest -vvs >> jenkins_launch.log 2>&1
diff -I '\[git daemon\].*' -I '.*port.*' -I '.*Change.*submitted.*' -I '.*127.0.0.1:.*' -I '.*Test CL.*' \
-I '.*Full commit ID.*' -I '.*create.*new_file.*' -I '.*drwxrwxr-x.*' -I '.*drwxr-xr-x.*' -I '.*-rwxrwxrwx.*' \
-I '.*-rw-rw-r--.*' -I '.*-rw-r--r--.*' -I '.*-r--r--r--.*' -I '.*drwx------.*' -I '.*Adding file.*' \
-I '\s*Created wheel for.*' -I '\s*Stored in directory.*' -I 'Requires: .*' -I 'Collecting .*' \
-I '\s*Downloading .*' -I '.* Cherry-picking .*' -I '.* Checking out .*' -I '.*THIS IS A TESTING VERSION.*' \
-I 'Fetched .* in .*' -I '.* passed, .* xfailed in .*' clear_launch.log jenkins_launch.log
exit $?
