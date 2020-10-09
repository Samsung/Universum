from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union
import copy
import os


__all__ = [
    "ProjectConfiguration",
    "Variations",
    "set_project_root",
    "get_project_root"
]


class ProjectConfiguration:
    """
    ProjectConfiguration is a collection of configurable project-specific data needed for Universum operations.
    Legacy constructor supports dictionary data, but for static type checking please use new explicit constructor.
    """

    # pylint: disable-msg=too-many-locals
    def __init__(self,
                 name: str = '',
                 command: Optional[List[str]] = None,
                 environment: Optional[Dict[str, str]] = None,
                 artifacts: str = '',
                 report_artifacts: str = '',
                 artifact_prebuild_clean: bool = False,
                 directory: str = '',
                 critical: bool = False,
                 background: bool = False,
                 finish_background: bool = False,
                 code_report: bool = False,
                 pass_tag: str = '',
                 fail_tag: str = '',
                 if_env_set: str = '',
                 extras: Optional[Dict[str, str]] = None,
                 **kwargs) -> None:  # explicit constructor for client's type safety
        self.name: str = name
        self.directory: str = directory
        self.code_report: bool = code_report
        self.command: List[str] = command if command else []
        self.environment: Dict[str, str] = environment if environment else {}
        self.artifacts: str = artifacts
        self.report_artifacts: str = report_artifacts
        self.artifact_prebuild_clean: bool = artifact_prebuild_clean
        self.critical: bool = critical
        self.background: bool = background
        self.finish_background: bool = finish_background
        self.pass_tag: str = pass_tag
        self.fail_tag: str = fail_tag
        self.if_env_set: str = if_env_set
        self.children: Optional['Variations'] = None
        self.extras: Dict[str, str] = extras if extras else {}
        for key, value in kwargs.items():
            self.extras[key] = value

    def __repr__(self) -> str:
        """
        This function simulates dict-like legacy representation for output
        :return: dict-like string

        >>> cfg = ProjectConfiguration(name='foo', command=['bar'], my_var='baz')
        >>> repr(cfg)
        "{'name': 'foo', 'command': 'bar', 'my_var': 'baz'}"
        """
        res = {k: v for k, v in self.__dict__.items() if v and k != 'extras'}
        res.update(self.extras)
        if len(self.command) == 1:  # command should be printed as one string, instead of list
            res['command'] = self.command[0]
        return str(res)

    def __eq__(self, other: Any) -> bool:
        """
        This functions simulates dict-like legacy comparison

        :param other: dict to compare values, or object to check exact equality
        :return: 'True' if 'other' matches

        >>> cfg1 = ProjectConfiguration(name='foo', my_var='bar')
        >>> cfg2 = ProjectConfiguration(name='foo', my_var='bar')
        >>> cfg3 = ProjectConfiguration(name='foo', my_var='bar', critical=True)
        >>> cfg1 == cfg1
        True
        >>> cfg1 == cfg2
        True
        >>> cfg1 == cfg3
        False
        >>> cfg1 == {'name': 'foo', 'my_var': 'bar'}
        True
        >>> cfg1 == {'name': 'foo', 'my_var': 'bar', 'critical': False}
        True
        >>> cfg1 == {'name': 'foo', 'my_var': 'bar', 'test': None}
        True
        >>> cfg1 == {'name': 'foo', 'my_var': 'bar', 'test': ' '}
        False
        """
        if isinstance(other, ProjectConfiguration):
            return self == other.__dict__
        if isinstance(other, dict):
            for key, val in other.items():
                if val and self[key] != val:
                    return False
            return True
        return super().__eq__(other)

    def __getitem__(self, item: str) -> Optional[str]:
        """
        This functions simulates dict-like legacy access

        :param item: client-defined item
        :return: client-defined value

        >>> cfg = ProjectConfiguration(name='foo', my_var='bar')
        >>> cfg['name']
        'foo'
        >>> cfg['my_var']
        'bar'
        >>> cfg['test']
        """
        return self.extras.get(item, self.__dict__.get(item, None))

    def __add__(self, other: 'ProjectConfiguration') -> 'ProjectConfiguration':
        """
        This functions defines operator ``+`` for :class:`.ProjectConfiguration` class objects by
        concatenating strings and contents of dictionaries

        :param other: `ProjectConfiguration` object
        :return: new `ProjectConfiguration` object, including all attributes from both `self` and `other` objects

        >>> cfg1 = ProjectConfiguration(name='foo', command=['foo'], critical=True, my_var1='foo')
        >>> cfg2 = ProjectConfiguration(name='bar', command=['bar'], background=True, my_var1='bar', my_var2='baz')
        >>> cfg1 + cfg2
        {'name': 'foobar', 'command': ['foo', 'bar'], 'background': True, 'my_var1': 'foobar', 'my_var2': 'baz'}
        """
        return ProjectConfiguration(
            name=self.name + other.name,
            command=self.command + other.command,
            environment=combine(self.environment, other.environment),
            artifacts=self.artifacts + other.artifacts,
            report_artifacts=self.report_artifacts + other.report_artifacts,
            artifact_prebuild_clean=self.artifact_prebuild_clean or other.artifact_prebuild_clean,
            directory=self.directory + other.directory,
            background=self.background or other.background,
            finish_background=self.finish_background or other.finish_background,
            code_report=self.code_report or other.code_report,
            pass_tag=self.pass_tag + other.pass_tag,
            fail_tag=self.fail_tag + other.fail_tag,
            if_env_set=self.if_env_set + other.if_env_set,
            extras=combine(self.extras, other.extras)
        )

    def replace_string(self, from_string: str, to_string: str) -> None:
        """
        Replace instances of a string, used for pseudo-variables

        :param from_string: string to replace, e.g. ${CODE_REPORT_FILE}
        :param to_string: value to put in place of 'from_string'

        >>> cfg = ProjectConfiguration(name='foo test', command=['foo', 'baz', 'foobar'], \
        myvar1='foo', myvar2='bar', myvar3=1)
        >>> cfg.replace_string('foo', 'bar')
        >>> cfg
        {'name': 'foo test', 'command': ['bar', 'baz', 'barbar'], 'myvar1': 'bar', 'myvar2': 'bar', 'myvar3': 1}

        >>> cfg = ProjectConfiguration(artifacts='foo', report_artifacts='foo', directory='foo')
        >>> cfg.replace_string('foo', 'bar')
        >>> cfg
        {'directory': 'bar', 'artifacts': 'bar', 'report_artifacts': 'bar'}
        """
        self.command = [word.replace(from_string, to_string) for word in self.command]
        self.artifacts = self.artifacts.replace(from_string, to_string)
        self.report_artifacts = self.report_artifacts.replace(from_string, to_string)
        self.directory = self.directory.replace(from_string, to_string)
        for k, v in self.extras.items():
            if isinstance(v, str):
                self.extras[k] = v.replace(from_string, to_string)

    def stringify_command(self) -> bool:
        """
        Concatenates components of a command into one element

        :return: 'True', if any of the command components have space inside

        >>> cfg = ProjectConfiguration(name='stringify test', command=['foo', 'bar', '--baz'])
        >>> cfg.stringify_command()
        False
        >>> cfg
        {'name': 'stringify test', 'command': 'foo bar --baz'}
        >>> cfg.stringify_command()
        True
        """
        result = False
        command_line = ""
        for argument in self.command:
            if " " in argument:
                argument = "\"" + argument + "\""
                result = True
            command_line = command_line + " " + argument if command_line else argument
        self.command = [command_line] if command_line else []
        return result


DictType = TypeVar('DictType', bound=dict)


def combine(dictionary_a: DictType, dictionary_b: DictType) -> DictType:
    # TODO: move to utils, as this is no longer specific to configurations
    """
    Combine two dictionaries using plus operator for matching keys

    :param dictionary_a: may have any keys and values
    :param dictionary_b: may have any keys, but the values of keys, matching `dictionary_a`,
        should be the compatible, so that 'dictionary_a'[key] + 'dictionary_b'[key] is a valid expression
    :return: new dictionary containing all keys from both `dictionary_a` and `dictionary_b`;
        for each matching key the value in resulting dictionary is a sum of two corresponding values

    For example:

    >>> combine(dict(attr_a = "a1", attr_b = ["b11", "b12"]), dict(attr_a = "a2", attr_b = ["b2"]))
    {'attr_a': 'a1a2', 'attr_b': ['b11', 'b12', 'b2']}

    >>> combine(dict(attr_a = {"a1": "v1"}, attr_b = {"b1": "v1"}), dict(attr_a = {"a2": "v2"}))
    {'attr_a': {'a1': 'v1', 'a2': 'v2'}, 'attr_b': {'b1': 'v1'}}

    """

    result = dictionary_a.__class__()
    for key in dictionary_a:
        if key in dictionary_b:
            if isinstance(dictionary_a[key], dict) and isinstance(dictionary_b[key], dict):
                # TODO: shouldn't we use recursion here?
                # also why not write result[key] = {**dictionary_a[key], **dictionary_b[key]} ?
                new_value = dictionary_a[key].copy()
                new_value.update(dictionary_b[key])
                result[key] = new_value
            else:
                result[key] = dictionary_a[key] + dictionary_b[key]
        else:
            result[key] = dictionary_a[key]

    for key in dictionary_b:
        if key not in dictionary_a:
            result[key] = dictionary_b[key]

    return result


class Variations:
    """
    `Variations` is a class for establishing project configurations.
    This class object is a list of dictionaries:

    >>> v1 = Variations([{"field1": "string"}])
    >>> v1.configs
    [{'field1': 'string'}]

    Build-in method all() generates iterable for all configuration dictionaries for further usage:

    >>> for i in v1.all(): i
    {'field1': 'string'}

    Built-in method dump() will generate a printable string representation of the object.
    This string will be printed into console output

    >>> v1.dump()
    "[{'field1': 'string'}]"

    Adding two objects will extend list of dictionaries:

    >>> v2 = Variations([{"field1": "line"}])
    >>> for i in (v1 + v2).all(): i
    {'field1': 'string'}
    {'field1': 'line'}

    While multiplying them will combine same fields of dictionaries:

    >>> for i in (v1 * v2).all(): i
    {'field1': 'stringline'}

    When a field value is a list itself -

    >>> v3 = Variations([dict(field2=["string"])])
    >>> v4 = Variations([dict(field2=["line"])])

    multiplying them will extend the inner list:

    >>> for i in (v3 * v4).all(): i
    {'field2': ['string', 'line']}

    """

    def __init__(self, lst: Optional[Union[List[Dict[str, Any]], List[ProjectConfiguration]]] = None):
        #  lst can be List[Dict[str, Any]] to support legacy cases - should be removed after project migration
        self.configs: List[ProjectConfiguration] = []  # aggregation is used instead of inheritance for type safety
        if lst:
            for item in lst:
                if isinstance(item, ProjectConfiguration):
                    self.configs.append(item)
                else:
                    self.configs.append(ProjectConfiguration(**item))

    def __eq__(self, other: Any) -> bool:
        """

        :param other:
        :return: 'True' if stored configurations match

        >>> l = [{'name': 'foo', 'critical': True}, {'name': 'bar', 'myvar': 'baz'}]
        >>> v1 = Variations(l)
        >>> cfg1 = ProjectConfiguration(name='foo', critical=True)
        >>> cfg2 = ProjectConfiguration(name='bar', myvar='baz')
        >>> v2 = Variations([cfg1]) + Variations([cfg2])
        >>> v3 = Variations() + Variations([l[0]]) + Variations([cfg2])
        >>> v1 == v1
        True
        >>> v1 == v2
        True
        >>> v1 == v3
        True
        >>> v1 == v2 + Variations()
        True
        >>> v1 == v1 * 1
        True
        >>> v1 == v1 * Variations()
        True
        >>> v1 == v2 + v3
        False
        """
        if isinstance(other, Variations):
            return self.configs == other.configs
        if isinstance(other, list):
            return self.configs == other
        return super().__eq__(other)

    def __bool__(self) -> bool:
        """
        This function defines truthiness of :class:`.Variations` object

        :return: 'True' if :class:`.Variations` class object is empty

        >>> v1 = Variations()
        >>> bool(v1)
        False
        >>> v2 = Variations([])
        >>> bool(v2)
        False
        >>> v3 = Variations([{}])
        >>> bool(v3)
        True
        """
        return len(self.configs) != 0

    def __getitem__(self, item: int) -> ProjectConfiguration:
        return self.configs[item]

    def __add__(self, other: Union['Variations', List[ProjectConfiguration]]) -> 'Variations':
        """
        This functions defines operator ``+`` for :class:`.Variations` class objects by
        concatenating lists of dictionaries into one list.
        The order of list members in resulting list is preserved: first all dictionaries from `self`,
        then all dictionaries from `other`.

        :param other: `Variations` object OR list of project configurations to be added to `configs`
        :return: new `Variations` object, including all configurations from both `self` and `other` objects
        """
        list_other: List[ProjectConfiguration] = other.configs if isinstance(other, Variations) else other
        return Variations(list.__add__(self.configs, list_other))

    def __mul__(self, other: Union['Variations', int]) -> 'Variations':
        """
        This functions defines operator ``*`` for :class:`.Variations` class objects.
        The resulting object is created by combining every `configs` list member with
        every `other` list member using :func:`.combine()` function.

        :param other: `Variations` object  OR an integer value to be multiplied to `self`
        :return: new `Variations` object, consisting of the list of combined configurations
        """
        if isinstance(other, int):
            return Variations(list.__mul__(self.configs, other))
        config_list: List[ProjectConfiguration] = []
        for obj_a in self.configs:
            obj_a_copy = copy.deepcopy(obj_a)
            if obj_a.children:
                obj_a_copy.children = obj_a.children * other
            else:
                obj_a_copy.children = copy.deepcopy(other)

            config_list.append(obj_a_copy)
        return Variations(config_list)

    def all(self) -> Iterable[ProjectConfiguration]:
        """
        Function for configuration iterating.

        :return: iterable for all dictionary objects in :class:`.Variations` list
        """
        for obj_a in self.configs:
            if obj_a.children:
                for obj_b in obj_a.children.all():
                    yield obj_a + obj_b
            else:
                yield copy.deepcopy(obj_a)

    def dump(self, produce_string_command: bool = True) -> str:
        """
        Function for :class:`.Variations` objects pretty printing.

        :param produce_string_command: if set to False, prints "command" as list instead of string
        :return: a user-friendly string representation of all configurations list
        """
        space_found: bool = False
        result: str = "["
        for obj in self.all():
            if len(result) > 1:
                result += ",\n"

            if produce_string_command and obj.stringify_command():
                space_found = True

            result += str(obj)

        result += "]"

        if space_found:
            result += "\n\nWARNING! We have detected space character within some of the command-line parameters.\n"
            result += "Please make sure you are not trying to pass two or more parameters as one."
        return result

    def filter(self, checker: Callable[[ProjectConfiguration], bool],
               parent: ProjectConfiguration = None) -> 'Variations':
        """
        This function is supposed to be called from main script, not configuration file.
        It uses provided `checker` to find all the configurations that pass the check,
        removing those not matching conditions.

        :param checker: a function that returns `True` if configuration passes the filter and `False` otherwise
        :param parent: an inner parameter for recursive usage; should be None when function is called from outside
        :return: new `Variations` object without configurations not matching `checker` conditions
        """

        if parent is None:
            parent = ProjectConfiguration()

        filtered_configs: Variations = Variations()

        for obj_a in self.configs:
            item: ProjectConfiguration = parent + obj_a

            if obj_a.children:
                active_children_configs = obj_a.children.filter(checker, item).configs
                if active_children_configs:
                    if len(active_children_configs) == 1:
                        obj_a_copy = obj_a + active_children_configs[0]
                        if active_children_configs[0].children:
                            obj_a_copy.children = active_children_configs[0].children
                        obj_a_copy.critical = \
                            obj_a.critical or active_children_configs[0].critical
                    else:
                        obj_a_copy = copy.deepcopy(obj_a)
                        obj_a_copy.children = Variations(active_children_configs)
                    filtered_configs += [obj_a_copy]
            else:
                if checker(item):
                    filtered_configs += [copy.deepcopy(obj_a)]

        return filtered_configs


global_project_root = os.getcwd()


def set_project_root(project_root: str) -> None:
    """
    Function to be called from main script; not supposed to be used in configuration file.
    Stores generated project location for further usage. This function is needed because
    project sources most likely will be copied to a temporary directory
    of some automatically generated location and the CI run will be performed there.

    :param project_root: path to actual project root
    """
    global global_project_root
    global_project_root = project_root


def get_project_root() -> str:
    """
    Function to be used in configuration file. Inserts actual project location after
    that location is generated. If project root is not set, function returns current directory.

    :return: actual project root
    """
    return os.path.abspath(global_project_root)
