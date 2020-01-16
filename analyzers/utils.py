# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import json
import sys


def add_common_arguments(parser):
    parser.add_argument("--result-file", dest="result_file",
                        help="File for storing json results of Universum run. Set it to \"${CODE_REPORT_FILE}\" "
                             "for running from Universum, variable will be handled during run. If you run this "
                             "script separately from Universum, just name the result file or leave it empty.")


def analyzers_output(json_file, issues_loads):
    issues = json.dumps(issues_loads, indent=4)
    if not json_file:
        sys.stdout.write(issues)
    else:
        with open(json_file, "wb") as outfile:
            outfile.write(issues)
