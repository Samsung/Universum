# feed.date.tools -- miscellaneous useful date/time functions

# This is the BSD license. For more information, see:
# http://www.opensource.org/licenses/bsd-license.php
#
# Copyright (c) 2006, Steve R. Hastings
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
# 
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
# 
#     * Neither the name of Steve R. Hastings nor the names
#       of any contributors may be used to endorse or promote products
#       derived from this software without specific prior written
#       permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
# OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.




"""
Miscellaneous date/time functions.

"tf" is short for "time float", a float being used as a time value
(seconds since the epoch).  Always store tf values as UTC values, not
local time values.  A TF of 0.0 means the epoch in UTC.


Please send questions, comments, and bug reports to: pyfeed@langri.com
"""


import re
import time



module_name = "feed.date.tools"
module_version = "0.7.4"
module_banner = "%s version %s" % (module_name, module_version)



# TF conversion functions

def local_from_utc(tf):
    """
    Take a time float with UTC time and return a tf with local time.
    """
    return tf - time.timezone

def utc_from_local(tf):
    """
    Take a time float with local time and return a tf with UTC time.
    """
    return tf + time.timezone



def tf_local():
    """
    Return a time float with the current time in local time.
    """
    return time.time() - time.timezone

def tf_utc():
    """
    Return a time float with the current time in UTC time.
    """
    return time.time()



# _tz_offset_dict
# Look up a time zone offset code and return an offset value.  Offset
# represents how many hours offset from UTC.

_tz_offset_dict = {
    "ut": 0, "utc": 0, "gmt": 0, "z": 0,
    "et": -5, "est": -5, "edt": -4,
    "ct": -6, "cst": -6, "cdt": -5,
    "mt": -7, "mst": -7, "mdt": -6,
    "pt": -8, "pst": -8, "pdt": -7,
    "a": -1, "b": -2, "c": -3, "d": -4, "e": -5, "f": -6, "g": -7,
    "h": -8, "i": -9, "k": -10, "l": -11, "m": -12, "n": +1, "o": +2,
    "p": +3, "q": +4, "r": +5, "s": +6, "t": +7, "u": +8, "v": +9,
    "w": +10, "x": +11, "y": +12}


_pat_time_offset = re.compile("([+-])(\d\d):?(\d\d?)?")

def parse_time_offset(s):
    """
    Given a time offset string, return the offset from UTC, in seconds.

    RSS allows any RFC822-compatible time offset, which includes many
    odd codes such as "EST", "PDT", "N", etc.  This function understands
    them all, plus numeric ones like "-0800".
    """
    # Python's time.strptime() function can understand numeric offset,
    # or text code, but not either one.

    if s is None:
        return 0

    try:
        s = s.lstrip().rstrip().lower()
    except AttributeError:
        raise TypeError, "time offset must be a string"

    if s in _tz_offset_dict:
        return _tz_offset_dict[s] * 3600

    m = _pat_time_offset.search(s)
    if not m:
        raise ValueError, "invalid time offset string"

    sign = m.group(1)
    offset_hour = int(m.group(2))
    if m.group(3) is not None:
        offset_min = int(m.group(3))
    else:
        offset_min = 0
    offset = offset_hour * 3600 + offset_min * 60

    if sign == "-":
        offset *= -1

    return offset



def tf_from_s(s):
    """
    Return a time float from a date string.  Try every format we know.
    """
    from feed.date.rfc3339 import tf_from_timestamp as tf_from_rfc3339
    from feed.date.rfc822 import tf_from_timestamp as tf_from_rfc822
    tf = tf_from_rfc3339(s)
    if tf is not None:
        return tf

    tf = tf_from_rfc822(s)
    if tf is not None:
        return tf

    return None



class TimeSeq(object):
    """
    A class to generate a sequence of timestamps.

    Atom feed validators complain if multiple timestamps have the same
    value, so this provides a convenient way to set a bunch of timestamps
    all at least one second different from each other.
    """
    def __init__(self, init_time=None):
        if init_time is None:
            self.tf = float(int(tf_utc()))
        else:
            self.tf = float(init_time)
    def next(self):
        tf = self.tf
        self.tf += 1.0
        return tf







if __name__ == "__main__":
    failed_tests = 0

    def self_test(message):
        """
        Check to see if a test failed; if so, print warnings.

        message: string to print on test failure

        Implicit arguments:
            failed_tests -- count of failed tests; will be incremented
            correct -- the expected result of the test
            result -- the actual result of the test
        """
        global failed_tests

        if result != correct:
            failed_tests += 1
            print module_banner
            print "test failed:", message
            print "    correct:", correct
            print "    result: ", result
            print


    correct = 1141607495.0
    result = utc_from_local(local_from_utc(correct))
    self_test("local/utc conversion test 0")

    correct = 1071340202.0
    result = tf_from_s("2003-12-13T18:30:02Z")
    self_test("tf_from_s() test 0")

    correct = 1143183379.0
    result = tf_from_s("2006-03-24 06:56:19.00Z")
    self_test("tf_from_s() test 1")

    correct = 1143142223.0
    result = tf_from_s("Thu, 23 Mar 2006  11.30.23.00 PST")
    self_test("tf_from_s() test 2")


    from sys import exit
    s_module = module_name + " " + module_version
    if failed_tests == 0:
        print s_module + " self-test: all tests succeeded!"
        exit(0)
    elif failed_tests == 1:
        print s_module + " self-test: 1 test failed."
        exit(1)
    else:
        print s_module + " self-test: %d tests failed." % failed_tests
        exit(1)
