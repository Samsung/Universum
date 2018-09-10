# -*- coding: UTF-8 -*-

import argparse
import os
import sys


class ModuleNamespace(argparse.Namespace):
    def __setattr__(self, name, value):
        if '.' in name:
            group, name = name.split('.', 1)
            ns = getattr(self, group, ModuleNamespace())
            setattr(ns, name, value)
            self.__dict__[group] = ns
        else:
            self.__dict__[name] = value

    def __getattr__(self, name):
        if '.' in name:
            group, name = name.split('.', 1)
            try:
                ns = self.__dict__[group]
            except KeyError:
                raise AttributeError("No attribute '" + name + "' in module arguments")
            return getattr(ns, name)
        else:
            raise AttributeError("No attribute '" + name + "' in module arguments")


# noinspection PyProtectedMember
# pylint: disable = protected-access
class ModuleArgumentGroup(argparse._ArgumentGroup):
    def __init__(self, container, *args, **kwargs):
        self.container = container
        super(ModuleArgumentGroup, self).__init__(container, *args, **kwargs)

    def _add_action(self, action):
        if action.metavar is not None:
            if 'sphinx' in sys.modules:
                action.help += "\n\nEnvironment variable: ${}".format(action.metavar)
            else:
                action.help += " [env: {}]".format(action.metavar)
            default = os.environ.get(action.metavar, action.default)

            if isinstance(action, (argparse._AppendAction, argparse._AppendConstAction)):
                if default is not None:
                    action.default = [default]
            else:
                action.default = default

        self.container.prepend_dest(action)

        return super(ModuleArgumentGroup, self)._add_action(action)

    def add_hidden_argument(self, *args, **kwargs):
        if kwargs.get("is_hidden", True):
            kwargs["help"] = argparse.SUPPRESS

        del kwargs["is_hidden"]
        self.add_argument(*args, **kwargs)

    def prepend_dest(self, action):
        self.container.prepend_dest(action)


class ModuleArgumentParser(argparse.ArgumentParser):

    def __init__(self, **kwargs):
        self.groups = dict()
        self.dest_prefix = ''
        argparse.ArgumentParser.__init__(self, **kwargs)

    def add_argument_group(self, *args, **kwargs):
        group = ModuleArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def get_or_create_group(self, title=None, description=None):

        if title not in self.groups:
            self.groups[title] = self.add_argument_group(title, description)

        return self.groups[title]

    def parse_args(self, args=None, namespace=None):
        """
        Parse passed arguments based on previous setup
        :param args: argument list to parse
        :param namespace: the resulting object to store settings to
        :return: object populated with all settings
        """
        if namespace is None:
            namespace = ModuleNamespace()

        return argparse.ArgumentParser.parse_args(self, args, namespace)

    def add_hidden_argument(self, *args, **kwargs):
        kwargs["help"] = argparse.SUPPRESS
        self.add_argument(*args, **kwargs)

    def prepend_dest(self, action):
        action.dest = self.dest_prefix + action.dest


class IncorrectParameterError(ValueError):
    pass
