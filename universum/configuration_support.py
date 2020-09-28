from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union
import copy
import os


__all__ = [
    "ProjectConfiguration",
    "Variations",
    "combine",
    "set_project_root",
    "get_project_root"
]

skip_attributes = {"children", "critical", "skip_numbering_level"}


class ProjectConfiguration(dict):  # dict inheritance is a temporary measure to simplify transition

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
                 **kwargs) -> None:  # explicit constructor for client's type safety
        self['name'] = name
        self['command'] = command if command else []
        self['environment'] = environment if environment else {}
        self['artifacts'] = artifacts
        self['report_artifacts'] = report_artifacts
        self['artifact_prebuild_clean'] = artifact_prebuild_clean
        self['directory'] = directory
        self['critical'] = critical
        self['background'] = background
        self['finish_background'] = finish_background
        self['code_report'] = code_report
        self['pass_tag'] = pass_tag
        self['fail_tag'] = fail_tag
        self['if_env_set'] = if_env_set
        for key, value in kwargs.items():
            self[key] = value

    @property
    def name(self) -> str:
        return self.get('name', '')

    @property
    def command(self) -> List[str]:
        return self.get('command', [])

    @property
    def environment(self) -> Dict[str, str]:
        return self.get('environment', {})

    @property
    def artifacts(self) -> str:
        return self.get('artifacts', '')

    @property
    def report_artifacts(self) -> str:
        return self.get('report_artifacts', '')

    @property
    def artifact_prebuild_clean(self) -> bool:
        return self.get('artifact_prebuild_clean', False)

    @property
    def directory(self) -> str:
        return self.get('directory', '')

    @property
    def critical(self) -> bool:
        return self.get('critical', False)

    @critical.setter
    def critical(self, val: bool) -> None:
        self['critical'] = val

    @property
    def background(self) -> bool:
        return self.get('background', False)

    @property
    def finish_background(self) -> bool:
        return self.get('finish_background', False)

    @property
    def code_report(self) -> bool:
        return self.get('code_report', False)

    @property
    def pass_tag(self) -> str:
        return self.get('pass_tag', '')

    @property
    def fail_tag(self) -> str:
        return self.get('fail_tag', '')

    @property
    def children(self) -> Optional['Variations']:
        return self.get('children', None)

    @children.setter
    def children(self, val: 'Variations') -> None:
        self['children'] = val

    @property
    def skip_numbering_level(self) -> bool:
        return self.get('skip_numbering_level', False)

    @skip_numbering_level.setter
    def skip_numbering_level(self, val: bool):
        self['skip_numbering_level'] = val

    def replace_string(self, from_string: str, to_string: str) -> None:
        for key, val in self.items():  # type: ignore #  https://github.com/python/mypy/issues/7981
            if key == 'command':
                self[key] = [word.replace(from_string, to_string) for word in val]
            else:
                if isinstance(val, str):
                    self[key] = val.replace(from_string, to_string)

    def __eq__(self, other):
        if isinstance(other, dict):
            return super().__eq__(ProjectConfiguration(**other))
        return super().__eq__(other)


DictType = TypeVar('DictType', bound=dict)


def combine(dictionary_a: DictType, dictionary_b: DictType) -> DictType:
    # this should probably be a method in ProjectConfiguration
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
        if key in skip_attributes:
            continue
        if key in dictionary_b:
            if isinstance(dictionary_a[key], dict) and isinstance(dictionary_b[key], dict):
                new_value = dictionary_a[key].copy()
                new_value.update(dictionary_b[key])
                result[key] = new_value
            else:
                result[key] = dictionary_a[key] + dictionary_b[key]
        else:
            result[key] = dictionary_a[key]

    for key in dictionary_b:
        if key in skip_attributes:
            continue
        if key not in dictionary_a:
            result[key] = dictionary_b[key]

    return result


def stringify(obj: Dict[str, str]) -> bool:
    result = False
    command_line = ""
    for argument in obj["command"]:
        if " " in argument:
            argument = "\"" + argument + "\""
            result = True

        if command_line == "":
            command_line = argument
        else:
            command_line += " " + argument

    obj["command"] = command_line
    return result


class Variations:
    """
    `Variations` is a class for establishing project configurations.
    This class object is a list of dictionaries:

    >>> v1 = Variations([{"field1": "string"}])
    >>> v1
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

    def __init__(self, lst: Optional[Union[List[Dict[str, Any]], List[ProjectConfiguration]]]):
        #  lst can be List[Dict[str, Any]] to support legacy cases - should be removed after project migration
        self.configs: List[ProjectConfiguration] = []  # aggregation is used instead of inheritance for type safety
        if lst:
            for item in lst:
                if isinstance(item, ProjectConfiguration):
                    self.configs.append(item)
                else:
                    self.configs.append(ProjectConfiguration(**item))

    def __eq__(self, other) -> bool:
        if isinstance(other, Variations):
            return self.configs == other.configs
        if isinstance(other, list):
            return self.configs == other
        return super().__eq__(other)

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
            obj_a_copy.skip_numbering_level = len(self.configs) <= 1

            config_list.append(obj_a_copy)
        return Variations(config_list)

    def all(self) -> Iterable[ProjectConfiguration]:
        """
        Function for configuration iterating.

        :return: iterable for all dictionary objects in :class:`.Variations` list
        """
        for obj_a in self.configs:

            obj_a_copy = copy.deepcopy(obj_a)

            if obj_a_copy.children:
                for obj_b in obj_a_copy.children.all():
                    res = combine(obj_a_copy, obj_b)

                    yield res
            else:
                yield obj_a_copy

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

            if produce_string_command and "command" in obj:
                if stringify(obj):
                    space_found = True

            result += str(obj)

        result += "]"

        if space_found:
            result += "\n\nWARNING! We have detected space character within some of the command-line parameters.\n"
            result += "Please make sure you are not trying to pass two or more parameters as one."
        return result

    def filter(self, checker: Callable[[ProjectConfiguration], bool], parent: ProjectConfiguration = None) -> 'Variations':
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

        filtered_configs: List[ProjectConfiguration] = []

        for obj_a in self.configs:
            item: ProjectConfiguration = combine(parent, copy.deepcopy(obj_a))

            if obj_a.children:
                active_children_configs = obj_a.children.filter(checker, item).configs
                if active_children_configs:
                    if len(active_children_configs) == 1:
                        obj_a_copy = combine(obj_a, active_children_configs[0])
                        if active_children_configs[0].children:
                            obj_a_copy.children = active_children_configs[0].children
                        obj_a_copy.critical = \
                            obj_a.critical or active_children_configs[0].critical
                    else:
                        obj_a_copy = copy.deepcopy(obj_a)
                        obj_a_copy.children = Variations(active_children_configs)
                    filtered_configs.append(obj_a_copy)
            else:
                if checker(item):
                    filtered_configs.append(copy.deepcopy(obj_a))

        return Variations(filtered_configs)


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
