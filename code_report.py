#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import sys

from analyzers.pylint_analyzer import PylintAnalyzer
from analyzers.svace_analyzer import SvaceAnalyzer
from analyzers.uncrustify_analyzer import UncrustifyAnalyzer


def define_arguments(parser):
    parser.add_argument("--type", dest="static_analyzer", choices=["pylint", "pylint3", "svace", "uncrustify"],
                        help="Define, which code report tool should be used.")
    parser.add_argument("--result-file", dest="result_file", help=argparse.SUPPRESS)


def main():
    parser = argparse.ArgumentParser()
    settings, analyzer_args = parser.parse_known_args(define_arguments(parser))

    if settings.static_analyzer in ["pylint", "pylint3"]:
        analyzer_namespace = PylintAnalyzer.define_arguments(parser, analyzer_args)
        analyze = PylintAnalyzer(analyzer_namespace, settings.static_analyzer, settings.result_file)
    elif settings.static_analyzer == "uncrustify":
        analyzer_parser = UncrustifyAnalyzer.define_arguments(parser)
        analyzer_settings = analyzer_parser.parse_args(analyzer_args)
        analyze = UncrustifyAnalyzer(analyzer_settings, settings.result_file)
    else:
        analyzer_namespace = SvaceAnalyzer.define_arguments(parser, analyzer_args)
        analyze = SvaceAnalyzer(analyzer_namespace, settings.static_analyzer, settings.result_file)
    return analyze.execute()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
