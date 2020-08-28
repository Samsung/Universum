from typing import Callable, Dict, Iterable, List, Union
import copy
import os
import six

__all__ = [
    "Variations",
    "combine",
    "set_project_root",
    "get_project_root"
]

skip_attributes = {"children", "critical", "skip_numbering_level"}


def combine(dictionary_a: Dict, dictionary_b: Dict) -> Dict:
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

    result = {}
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


class Variations(list):
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

    def __add__(self, other: List) -> 'Variations':
        """
        This functions defines operator ``+`` for :class:`.Variations` class objects by
        concatenating lists of dictionaries into one list.
        The order of list members in resulting list is preserved: first all dictionaries from `self`,
        then all dictionaries from `other`.

        :param other: `Variations` object OR list to be added to `self`
        :return: new `Variations` object, including all configurations from both `self` and `other` objects
        """
        return Variations(list.__add__(list(self), other))

    def __mul__(self, other: Union[int, 'Variations']) -> 'Variations':
        """
        This functions defines operator ``*`` for :class:`.Variations` class objects.
        The resulting object is created by combining every `self` list member with
        every `other` list member using :func:`.combine()` function.

        :param other: `Variations` object  OR an integer value to be multiplied to `self`
        :return: new `Variations` object, consisting of the list of combined configurations
        """

        if isinstance(other, six.integer_types):
            result_list: List = list.__mul__(list(self), other)
        else:
            result_list = []
            for obj_a in self:
                obj_a_copy = copy.deepcopy(obj_a)
                if "children" in obj_a:
                    obj_a_copy["children"] = obj_a["children"] * other
                else:
                    obj_a_copy["children"] = copy.deepcopy(other)
                obj_a_copy["skip_numbering_level"] = len(self) <= 1

                result_list.append(obj_a_copy)

        result = Variations(result_list)
        return result

    def all(self) -> Iterable[Dict]:
        """
        Function for configuration iterating.

        :return: iterable for all dictionary objects in :class:`.Variations` list
        """
        for obj_a in self:

            obj_a_copy = copy.deepcopy(obj_a)

            if "children" in obj_a_copy:
                for obj_b in obj_a_copy["children"].all():
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

    def filter(self, checker: Callable[..., bool], parent: Dict = None) -> 'Variations':
        """
        This function is supposed to be called from main script, not configuration file.
        It uses provided `checker` to find all the configurations that pass the check,
        removing those not matching conditions.

        :param checker: a function that returns `True` if configuration passes the filter and `False` otherwise
        :param parent: an inner parameter for recursive usage; should be None when function is called from outside
        :return: new `Variations` object without configurations not matching `checker` conditions
        """

        if parent is None:
            parent = dict()

        filtered_variations: List[Dict] = []

        for obj_a in self:
            item: Dict = combine(parent, copy.deepcopy(obj_a))

            if "children" in obj_a:
                active_children = obj_a["children"].filter(checker, item)
                if active_children:
                    if len(active_children) == 1:
                        obj_a_copy = combine(obj_a, active_children[0])
                        if "children" in active_children[0]:
                            obj_a_copy["children"] = active_children[0]["children"]
                        obj_a_copy["critical"] = \
                            obj_a.get("critical", False) or active_children[0].get("critical", False)
                    else:
                        obj_a_copy = copy.deepcopy(obj_a)
                        obj_a_copy["children"] = active_children
                    filtered_variations.append(obj_a_copy)
            else:
                if checker(item):
                    filtered_variations.append(copy.deepcopy(obj_a))

        return Variations(filtered_variations)


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
