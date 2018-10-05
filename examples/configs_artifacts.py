#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from _universum.configuration_support import Variations

mkdir = Variations([dict(name="Create directory", command=["mkdir", "-p"])])
mkfile = Variations([dict(name="Create file", command=["touch"])])
dirs1 = Variations([dict(name=" one/two{}/three".format(str(x)),
                         command=["one/two{}/three".format(str(x))]) for x in range(0, 6)])
files1 = Variations([dict(name=" one/two{}/three/file{}.txt".format(str(x), str(x)),
                          command=["one/two{}/three/file{}.txt".format(str(x), str(x))])
                     for x in range(0, 6)])

dirs2 = Variations([dict(name=" one/three", command=["one/three"])])
files2 = Variations([dict(name=" one/three/file.sh", command=["one/three/file.sh"])])

artifacts = Variations([dict(name="Existing artifacts", artifacts="one/**/file*", report_artifacts="one/*"),
                        dict(name="Missing artifacts", artifacts="something", report_artifacts="something_else")])

configs = mkdir * dirs1 + mkdir * dirs2 + mkfile * files1 + mkfile * files2 + artifacts

if __name__ == '__main__':
    print configs.dump()
