# pylint: disable = protected-access

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
        if not '.' in name:
            raise AttributeError("No attribute '" + name + "' in module arguments")

        group, name = name.split('.', 1)
        try:
            ns = self.__dict__[group]
        except KeyError as error:
            raise AttributeError("No attribute '" + name + "' in module arguments") from error
        return getattr(ns, name)


# noinspection PyProtectedMember
class ModuleArgumentGroup(argparse._ArgumentGroup):
    def __init__(self, container, *args, **kwargs):
        self.container = container
        super().__init__(container, *args, **kwargs)

    def _add_action(self, action):
        if action.metavar is not None:
            try:
                if 'sphinx' in sys.modules:
                    action.help += f"\n\nEnvironment variable: ${action.metavar}"
                else:
                    if not isinstance(action, argparse._SubParsersAction):
                        action.help += f" [env: {action.metavar}]"
            except TypeError:
                action.help = f"Also available as [env: {action.metavar}]"
            default = os.environ.get(action.metavar, action.default)

            if isinstance(action, (argparse._AppendAction, argparse._AppendConstAction)):
                if default is not None:
                    action.default = [default]
            else:
                action.default = default

        self.container.prepend_dest(action)

        return super()._add_action(action)

    def add_hidden_argument(self, *args, **kwargs):
        if kwargs.get("is_hidden", True):
            kwargs["help"] = argparse.SUPPRESS

        del kwargs["is_hidden"]
        self.add_argument(*args, **kwargs)

    def prepend_dest(self, action):
        self.container.prepend_dest(action)


# noinspection PyProtectedMember
class ModuleArgumentParser(argparse.ArgumentParser):

    def __init__(self, **kwargs):
        self.groups = {}
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

        if args is None:
            args = sys.argv[1:]

        self._add_default_parser(args)

        return argparse.ArgumentParser.parse_args(self, args, namespace)

    def add_hidden_argument(self, *args, **kwargs):
        kwargs["help"] = argparse.SUPPRESS
        self.add_argument(*args, **kwargs)

    def prepend_dest(self, action):
        action.dest = self.dest_prefix + action.dest

    def _get_subparsers_action(self):
        if not self._subparsers:
            return None

        for action in self._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                return action

        return None

    @staticmethod
    def _needs_default_parser(subparsers_action, args):
        try:
            possible_subcommand = args[0]
        except IndexError:
            return True

        for sp_name in subparsers_action._name_parser_map.keys():
            if sp_name == possible_subcommand:
                return False

        return True

    def _add_default_parser(self, args):
        """
        We need to manually add the default parser because of subcommand's arguments intersection.
        1. We need subcommands for namespaces and help messages to be ajustable in different Universum modes.
        2. If a subcommand is passed, and arguments in parser and subparser intersect, all values passed to
           non-subparser are ignored; so without default subparser ``universum -vt=p4 submit`` will result in
           undefined value of 'vcs_type', and ``universum -vt=p4 submit -vt=git`` will result in 'git' value.
           Adding default subparser allows to avoid such unexpected behaviour.
        3. Also if arguments of 'general' parser and a subparser intersect, the environment variables are
           stored to 'general' parser (and then ignored as described above).
        """
        subparsers_action = self._get_subparsers_action()
        if not subparsers_action:
            return
        if not self._needs_default_parser(subparsers_action, args):
            return

        default = "default"
        subparsers_action.add_parser(default)
        args.insert(len(args), default)


class IncorrectParameterError(ValueError):
    pass
