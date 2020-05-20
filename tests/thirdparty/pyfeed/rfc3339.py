# feed.date.rfc3339 -- conversion functions for RFC 3339 timestamps

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
Conversion functions to handle RFC 3339 timestamp format.

RFC 3339 format is used in Atom syndication feeds.

"tf" is short for "time float", a float being used as a time value
(seconds since the epoch).  Always store tf values as UTC values, not
local time values.  A TF of 0.0 means the epoch in UTC.


Please send questions, comments, and bug reports to: pyfeed@langri.com

"""



import re
import time

from calendar import timegm
from .tools import tf_utc
from .tools import parse_time_offset



module_name = "feed.date.rfc3339"
module_version = "0.7.4"
module_banner = "%s version %s" % (module_name, module_version)



# NOTES ON TIME CONVERSIONS
#
# Most of the time, the tf values will be UTC (aka GMT or Zulu time)
# values.  Timestamp strings come complete with time offset specifiers,
# so when you convert a timestamp to a tf, the time offset will cause an
# adjustment to the tf to make it a UTC value.
#
# Then, we use Python's time conversion functions that work on UTC
# values, so we don't get any adjustments for local time.
#
# Finally, when actually formatting the timestamp string for output, we
# calculate the adjustment for the offset value.  If you print a
# timestamp value with a "Z" offset value, you get no adjustment; if you
# use "-0800", you get an 8 hour adjustment; and so on.
#
# These two timestamps both represent the same time:
#
# 1969-12-31T16:00:01-08:00
# 1970-01-01T00:00:01Z
#
# They are both a tf of 1.0.



def cleanup_time_offset(time_offset):
    """
    Given a time offset, return a time offset in a consistent format.

    If the offset is for UTC, always return a "Z".

    Otherwise, return offset in this format: "(+|-)hh:mm"
    """
    secs = parse_time_offset(time_offset)

    if secs == 0:
        return "Z"

    return s_time_offset_from_secs(secs)



_format_RFC3339 = "%Y-%m-%dT%H:%M:%S"

def timestamp_from_tf(tf, time_offset=None):
    """
    Format a time and offset into a string.

    Arguments:
        tf
            a floating-point time value, seconds since the epoch.
        time_offset
            a string specifying an offset from UTC.  Examples:
            z or Z -- offset is 0 ("Zulu" time, UTC, aka GMT)
            -08:00 -- 8 hours earlier than UTC (Pacific time zone)
            "" -- empty string is technically not legal, but may work

    Notes:
        Returned string complies with RFC 3339.
        Example: 2003-12-13T18:30:02Z
        Example: 2003-12-13T18:30:02+02:00
    """

    if tf is None:
        return ""

    if time_offset is None:
        time_offset = s_offset_default


    # converting from tf to timestamp so *add* time offset
    tf += parse_time_offset(time_offset)

    try:
        s = time.strftime(_format_RFC3339, time.gmtime(tf))
    except ValueError:
        return "<!-- date out of range; tf is %.1f -->" % tf

    return s + time_offset



# date recognition pattern

# This is *extremely* permissive as to what it accepts!
# Long form regular expression with lots of comments.

_pat_rfc3339 = re.compile(r"""
(\d\d\d\d)\D+(\d\d)\D+(\d\d)  # year month day, separated by non-digit
\D+  # non-digit
(\d\d?)\D+(\d\d)\D+(\d\d)  # hour minute sec, separated by non-digit
([.,]\d+)?  # optional fractional seconds (American decimal or Euro ",")
\s*  # optional whitespace
(\w+|[-+]\d\d?\D*\d\d)?  # time offset: letter(s), or +/- hours:minutes
""", re.X)

def tf_from_timestamp(timestamp):
    """
    Take a RFC 3339 timestamp string and return a time float value.

    timestamp example: 2003-12-13T18:30:02Z
    timestamp example: 2003-12-13T18:30:02+02:00

    Leaving off the suffix is technically not legal, but allowed.
    """

    timestamp = timestamp.lstrip().rstrip()

    try:
        m = _pat_rfc3339.search(timestamp)
        year = int(m.group(1))
        mon = int(m.group(2))
        mday = int(m.group(3))
        hour = int(m.group(4))
        min = int(m.group(5))
        sec = int(m.group(6))
        s_zone_offset = m.group(8)

        tup = (year, mon, mday, hour, min, sec, -1, -1, 0)

        # calendar.timegm() is like time.mktime() but doesn't adjust
        # from local to UTC; it just converts to a tf.
        tf = timegm(tup)

        # Use time offset from timestamp to adjust from UTC to correct.
        # If s_zone_offset is "GMT", "UTC", or "Z", offset is 0.

        # converting from timestamp to tf so *subtract* time offset
        tf -= parse_time_offset(s_zone_offset)
    except:
        return None

    return float(tf)



def s_time_offset_from_secs(secs):
    """
    Return a string with offset from UTC in RFC3339 format, from secs.

    """

    if secs > 0:
        sign = "+"
    else:
        sign = "-"
        secs = abs(secs)

    offset_hour = secs // (60 * 60)
    offset_min = (secs // 60) % 60
    return "%s%02d:%02d" % (sign, offset_hour, offset_min)


def local_time_offset():
    """
    Return a string with local offset from UTC in RFC3339 format.
    """

    # If tf is set to local time in seconds since the epoch, then...
    # ...offset is the value you add to tf to get UTC.  This is the
    # reverse of time.timezone or time.altzone.

    if time.daylight:
        secs_offset = -(time.altzone)
    else:
        secs_offset = -(time.timezone)

    return s_time_offset_from_secs(secs_offset)

s_offset_local = local_time_offset()

offset_default = 0
s_offset_default = ""

def set_default_time_offset(s):
    global offset_default
    global s_offset_default
    offset_default = parse_time_offset(s)
    s_offset_default = s

set_default_time_offset(s_offset_local)



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
            print(module_banner)
            print("test failed:", message)
            print("    correct:", correct)
            print("    result: ", result)
            print()


    # The default is to make time stamps in local time with appropriate
    # offset; for the tests, we want a "Z" offset default instead.
    set_default_time_offset("Z")


    # Test: convert current time into a timestamp string and back

    tf_now = tf_utc()
    # timestamp format does not allow fractional seconds
    correct = float(int(tf_now))  # truncate any fractional seconds
    s = timestamp_from_tf(tf_now)
    result = tf_from_timestamp(s)
    self_test("convert tf to timestamp and back 0")


    # Test: convert a timestamp string to a time value and back

    correct = "2003-12-13T18:30:02-07:00"
    tf = tf_from_timestamp(correct)
    result = timestamp_from_tf(tf, "-07:00")
    self_test("convert timestamp to tf and back 0")


    # Test: convert a timestamp string to a time value and back

    s_test = "2003-06-10T00:00:00-08:00"
    tf = tf_from_timestamp(s_test)
    result = timestamp_from_tf(tf, "Z")
    correct = "2003-06-10T08:00:00Z"
    self_test("convert timestamp to tf and back 1")


    # Test: convert a tf to a a timestamp string

    correct = "2006-04-07T11:38:34-07:00"
    result = timestamp_from_tf(1144435114, "-07:00")
    self_test("convert tf to timestamp 0")



    from sys import exit
    s_module = module_name + " " + module_version
    if failed_tests == 0:
        print(s_module + ": self-test: all tests succeeded!")
        exit(0)
    elif failed_tests == 1:
        print(s_module + " self-test: 1 test failed.")
        exit(1)
    else:
        print(s_module + " self-test: %d tests failed." % failed_tests)
        exit(1)
