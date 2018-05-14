#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import sys

from analyzers.pylint_analyzer import PylintAnalyzer


def define_arguments(parser):
    parser.add_argument("--type", dest="static_analyzer", choices=["pylint", "pylint3"],
                        help="Define, which code report tool should be used.")


def main():
    parser = argparse.ArgumentParser()
    settings, analyzer_args = parser.parse_known_args(define_arguments(parser))
    analyzer_namespace = PylintAnalyzer.define_arguments(parser, analyzer_args)
    analyze = PylintAnalyzer(analyzer_namespace, settings.static_analyzer)
    return analyze.execute()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
