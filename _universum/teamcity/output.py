# -*- coding: UTF-8 -*-

from ..base_classes import OutputBase

__all__ = [
    "TeamCityOutput"
]


def escape(message):
    return message.replace('\r', '').replace('|', '||').replace('\'', '|\'').replace('[', '|[').replace(']', '|]')


class TeamCityOutput(OutputBase):
    def open_block(self, num_str, name):
        print "##teamcity[blockOpened name='{} {}']".format(num_str, escape(name))

    def close_block(self, num_str, name, status):
        print "##teamcity[blockClosed name='{} {}']".format(num_str, escape(name))

    def report_error(self, description):
        print "##teamcity[buildProblem description='<{}>']".format(escape(description))

    def report_skipped(self, message):
        lines = message.split("\n")
        for single_line in lines:
            print u"##teamcity[message text='{}' status='WARNING']".format(escape(single_line))

    def change_status(self, message):
        print "##teamcity[buildStatus text='{}']".format(escape(message))

    def log_exception(self, line):
        lines = line.split("\n")
        for single_line in lines:
            print u"##teamcity[message text='{}' status='ERROR']".format(escape(single_line))

    def log_stderr(self, line):
        lines = line.split("\n")
        for single_line in lines:
            print u"##teamcity[message text='{}' status='WARNING']".format(escape(single_line))

    def log(self, line):
        print "==>", line

    def log_external_command(self, command):
        print "$", command

    def log_shell_output(self, line):
        print line
