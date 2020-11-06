# pylint: disable-msg=line-too-long
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union
from warnings import warn
import copy
import os


__all__ = [
    "Step",
    "Configuration",
    "set_project_root",
    "get_project_root"
]


class Step:
    """
    An instance of this class defines a single launch of an external command by Universum. It determines execution
    parameters and result handling. Individual build steps are collected in a :class:`Configuration` object, that
    allows to create linear and nested step structures.
    See https://universum.readthedocs.io/en/latest/configuring.html#build-step for details.

    **Step keys**

    Parameters supplied via named attributes during construction are annotated and can be type-checked for safety.
    Users may also define custom parameters in `kwargs` - these parameters will be stored internally in `dict` fields
    and can be retrieved by indexing. The following list enumerates all the keys used by Universum:

    name
        The human-readable name of a build step. The name is used as the title of the build log block
        corresponding to the execution of this step. It is also used to generate name of the log file if the option
        for storing to log files is selected. If several build steps have the same names, and logs are stored to
        files (see ``--out`` / ``-o``  command-line parameter for details), all logs for such
        steps will be stored to one file in order of their appearances.
    command
        The command line for the build step launch. For every step the first list
        item should be a console command (e.g. script name, or any other command like ``ls``), and other list items
        should be the arguments, added to the command (e.g. ``--debug`` or ``-la``). Every command line element,
        separated with space character, should be passed as a separate string argument. Lists like ``["ls -a"]``
        will not be processed correctly and therefore should be splat into ``["ls", "-a"]``. Lists like
        ``["build.sh", "--platform A"]`` will not be processed correctly and thus should be plat into
        ``["build.sh", "--platform", "A"]``. A build step can have an empty list as a command - such step won't do
        anything except showing up the step name in Universum execution logs. Some common actions, such as ``echo``
        or ``cp``, are bash features and not actual programs to run. These features should be called as
        ``["bash", "-c", "echo -e 'Some line goes here'"]``. Note that in this case the string to be passed to bash
        is one argument containing white spaces and therefore not splat by commas.
    environment
        Required environment variables, e.g. ``environment={"VAR1": "String", "VAR2": "123"}`` Can be set at any
        step level, but re-declaring variables is not supported, so please make sure to mention every variable only
        one time at most.
    artifacts
        Path to the file or directory to be copied to the working directory as an execution
        result. Can contain shell-style pattern matching (e.g. `"out/*.html"`), including recursive wildcards
        (e.g. `"out/**/index.html"`). If not stated otherwise (see ``--no-archive``
        command-line parameter for details), artifact directories are copied
        as archives. If `artifact_prebuild_clean` key is either absent or set to `False`
        and stated artifacts are present in downloaded sources, it is considered a failure and configuration
        execution will not proceed. If no required artifacts were found in the end of the `Universum` run, it is
        also considered a failure. In case of shell-style patterns build is failed if no files or directories
        matching pattern are found.
    report_artifacts
        Path to the special artifacts for reporting (e.g. to Swarm). Unlike `artifacts` key, `report_artifacts`
        are not obligatory and their absence is not considered a build failure. A directory cannot be stored
        as a separate artifact, so when using ``--no-archive`` option, do not claim directories as `report_artifacts`.
        Please note that any file can be put as `artifact`, `report_artifact`, or both. A file that is both
        in `artifacts` and `report_artifacts`, will be mentioned in a report and will cause build failure when missing.
    artifact_prebuild_clean
        A flag to signal that artifacts must be cleaned before the build. Cleaning of single files, directories and
        sets of files defined by shell-style patterns is supported. By default, artifacts are not stored in VCS, and
        artifact presence before build most likely means that working directory is not cleaned after previous build and
        therefore might influence build results. But sometimes deliverables have to be stored in VCS, and in this case
        instead of stopping the build they should be simply cleaned before it. This is where
        ``artifact_prebuild_clean=True`` key is supposed to be used. This flag is ignored, if both `artifacts` and
        `report_artifacts` are not set.
    directory
        Path to a current working directory for launched process. Absent
        `directory` has equal meaning to empty string passed as a `directory` value and means that `command`
        will be launched from the project root directory. See
        https://universum.readthedocs.io/en/latest/configuring.html#execution-directory for details.
    critical
        A flag used in case of a linear step execution, when the result of some step is critical
        for the subsequent step execution. If some step has `critical` key set to `True` and executing this step
        fails, no more steps will be executed during this run. However, all background steps, which have already
        started will be finished regardless of critical step results.
    background
        A flag used to signal that the current step should be executed independently in parallel with
        all other steps. All logs from such steps are written to file, and the results of execution are collected
        in the end of `Universum` run. Next step execution begins immediately after starting a background step,
        not waiting for it to be completed. Several background steps can be executed simultaneously.
    finish_background
        A flag used to signal that the current step should be executed only after ongoing
        background steps (if any) are finished.
    code_report
        A flag used to signal that the current step performs static or syntax analysis of the code.
        Usually set in conjunction with adding ``--result-file="${CODE_REPORT_FILE}"`` to 'command' arguments.
        Analyzers currently provided by Universum are: ``pylint``, ``svace`` and ``uncrustify``.
        See https://universum.readthedocs.io/en/latest/code_report.html for details.
    pass_tag
        A tag used to mark successful TeamCity builds. This tag can be set independenty
        of `fail_tag` value per each step. The value should be set to a strings without spaces as acceptable by
        TeamCity as tags. Every tag is added (if matching condition) after executing build step it is set in,
        not in the end of all run.
    fail_tag
        A tag used to mark failed TemCity builds. See `pass_tag` for details.

    Each parameter is optional, and is substituted with a falsy value, if omitted.

    :Example of a simple Step construction:

    >>> Step(foo='bar')
    {'foo': 'bar'}
    >>> cfg = Step(name='foo', command=['1', '2', '3'], _extras={'_extras': 'test', 'bool': True}, myvar=1)
    >>> cfg
    {'name': 'foo', 'command': ['1', '2', '3'], '_extras': {'_extras': 'test', 'bool': True}, 'myvar': 1}
    >>> cfg['name']
    'foo'
    >>> cfg['_extras']
    {'_extras': 'test', 'bool': True}
    >>> cfg['myvar']
    1

    :Example of using Configuration objects to wrap individual build steps:

    >>> make = Configuration([Step(name="Make ", command=["make"], pass_tag="pass_")])
    >>> target = Configuration([
    ...              Step(name="Linux", command=["--platform", "Linux"], pass_tag="Linux"),
    ...              Step(name="Windows", command=["--platform", "Windows"], pass_tag="Windows")
    ...          ])
    >>> configs = make * target
    >>> configs.dump()
    "[{'name': 'Make Linux', 'command': 'make --platform Linux', 'pass_tag': 'pass_Linux'},\\n{'name': 'Make Windows', 'command': 'make --platform Windows', 'pass_tag': 'pass_Windows'}]"

    This means that tags "pass_Linux" and "pass_Windows" will be sent to TeamCity's build.

    .. note:: All the paths, specified in `command`, `artifacts` and `directory` parameters, can be absolute or
        relative. All relative paths start from the project root (see :ref:`get_project_root`).
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
                 **kwargs) -> None:
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
        self.children: Optional['Configuration'] = None
        self._extras: Dict[str, str] = {}
        for key, value in kwargs.items():
            self._extras[key] = value

    def __repr__(self) -> str:
        """
        This function simulates `dict`-like representation for string output. This is useful when printing contents of
        :class:`Configuration` objects, as internally they wrap a list of :class:`Step` objects

        :return: a `dict`-like string

        >>> cfg = Step(name='foo', command=['bar'], my_var='baz')
        >>> repr(cfg)
        "{'name': 'foo', 'command': 'bar', 'my_var': 'baz'}"
        """
        res = {k: v for k, v in self.__dict__.items() if v and k != '_extras'}
        res.update(self._extras)
        if len(self.command) == 1:  # command should be printed as one string, instead of list
            res['command'] = self.command[0]
        return str(res)

    def __eq__(self, other: Any) -> bool:
        """
        This functions simulates `dict`-like check for match

        :param other: `dict` to compare values, or :class:`Step` object to check equality
        :return: `True` if `other` matches

        >>> cfg1 = Step(name='foo', my_var='bar')
        >>> cfg2 = Step(name='foo', my_var='bar')
        >>> cfg3 = Step(name='foo', my_var='bar', critical=True)
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
        >>> cfg1 == {'name': 'foo', 'my_var': 'bar', 'test': ''}
        True
        >>> cfg1 == {'name': 'foo', 'my_var': 'bar', 'test': ' '}
        False
        """
        if isinstance(other, Step):
            return self == other.__dict__
        if isinstance(other, dict):
            for key, val in other.items():
                if val and self[key] != val:
                    return False
            return True
        return super().__eq__(other)

    def __getitem__(self, item: str) -> Optional[str]:
        """
        This functions simulates `dict`-like legacy read access

        :param item: client-defined item
        :return: client-defined value

        >>> cfg = Step(name='foo', my_var='bar')
        >>> cfg['name']
        'foo'
        >>> cfg['my_var']
        'bar'
        >>> cfg['test']
        """
        #  _extras are checked first - just in case _extras field is added manually
        # do note that __setitem__ checks predefined fields first, however it's impossible to shadow them by
        # modifying _extras
        return self._extras.get(item, self.__dict__.get(item, None))

    def __setitem__(self, key: str, value: Any) -> None:
        """
        This functions simulates `dict`-like legacy write access

        :param key: client-defined key
        :param value: client-defined value

        >>> import warnings
        >>> def set_cfg_and_get_warnings(c, k, v):
        ...     with warnings.catch_warnings(record=True) as w:
        ...         warnings.simplefilter("always")
        ...         c[k] = v
        ...         return w
        >>> cfg = Step(name='foo', my_var='bar')
        >>> set_cfg_and_get_warnings(cfg, 'name', 'bar')  # doctest: +ELLIPSIS
        [<warnings.WarningMessage object at ...>]
        >>> set_cfg_and_get_warnings(cfg, 'directory', 'foo')  # doctest: +ELLIPSIS
        [<warnings.WarningMessage object at ...>]
        >>> set_cfg_and_get_warnings(cfg, 'test', 42)
        []
        >>> set_cfg_and_get_warnings(cfg, '_extras', {'name': 'baz'})
        []
        >>> cfg
        {'name': 'bar', 'directory': 'foo', 'my_var': 'bar', 'test': 42, '_extras': {'name': 'baz'}}
        >>> cfg['name']
        'bar'
        """
        if key in self.__dict__ and key != '_extras':
            warn("Re-defining the value of Step field. Please use var." + key + " to set it instead of "
                 "using var['" + key + "']")
            self.__dict__[key] = value
        else:
            self._extras[key] = value

    def __add__(self, other: 'Step') -> 'Step':
        """
        This functions defines operator ``+`` for :class:`Step` class objects by
        concatenating strings and contents of dictionaries. Note that `critical` attribute is not merged.

        :param other: `Step` object
        :return: new `Step` object, including all attributes from both `self` and `other` objects

        >>> cfg1 = Step(name='foo', command=['foo'], critical=True, my_var1='foo')
        >>> cfg2 = Step(name='bar', command=['bar'], background=True, my_var1='bar', my_var2='baz')
        >>> cfg1 + cfg2
        {'name': 'foobar', 'command': ['foo', 'bar'], 'background': True, 'my_var1': 'foobar', 'my_var2': 'baz'}
        """
        return Step(
            name=self.name + other.name,
            command=self.command + other.command,
            environment=combine(self.environment, other.environment),
            artifacts=self.artifacts + other.artifacts,
            report_artifacts=self.report_artifacts + other.report_artifacts,
            artifact_prebuild_clean=self.artifact_prebuild_clean or other.artifact_prebuild_clean,
            directory=self.directory + other.directory,
            critical=False,
            background=self.background or other.background,
            finish_background=self.finish_background or other.finish_background,
            code_report=self.code_report or other.code_report,
            pass_tag=self.pass_tag + other.pass_tag,
            fail_tag=self.fail_tag + other.fail_tag,
            if_env_set=self.if_env_set + other.if_env_set,
            **combine(self._extras, other._extras)
        )

    def replace_string(self, from_string: str, to_string: str) -> None:
        """
        Replace instances of a string, used for pseudo-variables

        :param from_string: string to replace, e.g. `${CODE_REPORT_FILE}`
        :param to_string: value to put in place of `from_string`

        >>> cfg = Step(name='foo test', command=['foo', 'baz', 'foobar'], myvar1='foo', myvar2='bar', myvar3=1)
        >>> cfg.replace_string('foo', 'bar')
        >>> cfg
        {'name': 'foo test', 'command': ['bar', 'baz', 'barbar'], 'myvar1': 'bar', 'myvar2': 'bar', 'myvar3': 1}

        >>> cfg = Step(artifacts='foo', report_artifacts='foo', directory='foo')
        >>> cfg.replace_string('foo', 'bar')
        >>> cfg
        {'directory': 'bar', 'artifacts': 'bar', 'report_artifacts': 'bar'}
        """
        self.command = [word.replace(from_string, to_string) for word in self.command]
        self.artifacts = self.artifacts.replace(from_string, to_string)
        self.report_artifacts = self.report_artifacts.replace(from_string, to_string)
        self.directory = self.directory.replace(from_string, to_string)
        for k, v in self._extras.items():
            if isinstance(v, str):
                self._extras[k] = v.replace(from_string, to_string)

    def stringify_command(self) -> bool:
        """
        Concatenates components of a command into one element

        :return: `True`, if any of the command components have space inside

        >>> cfg = Step(name='stringify test', command=['foo', 'bar', '--baz'])
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
        should be the compatible, so that `dictionary_a[key] + dictionary_b[key]` is a valid expression
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


class Configuration:
    """
    Configuration is a class for establishing project configurations. Each Configuration object wraps a list of build
    steps either from a pre-constructed :class:`Step` objects, or from the supplied `dict` data.

    >>> v1 = Configuration([{"field1": "string"}])
    >>> v1.configs
    [{'field1': 'string'}]

    Build-in method :meth:`.all()` generates iterable for all configuration dictionaries for further usage:

    >>> for i in v1.all(): i
    {'field1': 'string'}

    Built-in method :meth:`.dump()` will generate a printable string representation of the object.
    This string will be printed into console output

    >>> v1.dump()
    "[{'field1': 'string'}]"

    Adding two objects will extend list of dictionaries:

    >>> v2 = Configuration([{"field1": "line"}])
    >>> for i in (v1 + v2).all(): i
    {'field1': 'string'}
    {'field1': 'line'}

    While multiplying them will combine same fields of dictionaries:

    >>> for i in (v1 * v2).all(): i
    {'field1': 'stringline'}

    When a field value is a list itself -

    >>> v3 = Configuration([dict(field2=["string"])])
    >>> v4 = Configuration([dict(field2=["line"])])

    multiplying them will extend the inner list:

    >>> for i in (v3 * v4).all(): i
    {'field2': ['string', 'line']}

    """

    def __init__(self, lst: Optional[Union[List[Dict[str, Any]], List[Step]]] = None):
        #  lst can be List[Dict[str, Any]] to support legacy cases - should be removed after project migration
        self.configs: List[Step] = []  # aggregation is used instead of inheritance for type safety
        if lst:
            for item in lst:
                if isinstance(item, Step):
                    self.configs.append(item)
                else:
                    self.configs.append(Step(**item))

    def __eq__(self, other: Any) -> bool:
        """
        This function checks wrapped configurations for match

        :param other: :class:`Configuration` object or list of :class:`Step` objects
        :return: `True` if stored configurations match

        >>> l = [{'name': 'foo', 'critical': True}, {'name': 'bar', 'myvar': 'baz'}]
        >>> v1 = Configuration(l)
        >>> cfg1 = Step(name='foo', critical=True)
        >>> cfg2 = Step(name='bar', myvar='baz')
        >>> v2 = Configuration([cfg1]) + Configuration([cfg2])
        >>> v3 = Configuration() + Configuration([l[0]]) + Configuration([cfg2])
        >>> v1 == v1
        True
        >>> v1 == v2
        True
        >>> v1 == v3
        True
        >>> v1 == v1 + Configuration()
        True
        >>> v1 == v1 * 1
        True
        >>> v1 == v1 * Configuration()
        True
        >>> v1 == v2 + v3
        False
        """
        if isinstance(other, Configuration):
            return self.configs == other.configs
        if isinstance(other, list):
            return self.configs == other
        return super().__eq__(other)

    def __bool__(self) -> bool:
        """
        This function defines truthiness of :class:`Configuration` object

        :return: `True` if :class:`Configuration` class object is empty

        >>> v1 = Configuration()
        >>> bool(v1)
        False
        >>> v2 = Configuration([])
        >>> bool(v2)
        False
        >>> v3 = Configuration([{}])
        >>> bool(v3)
        True
        """
        return len(self.configs) != 0

    def __getitem__(self, item: int) -> Step:
        return self.configs[item]

    def __add__(self, other: Union['Configuration', List[Step]]) -> 'Configuration':
        """
        This functions defines operator ``+`` for :class:`Configuration` class objects by
        concatenating lists of dictionaries into one list.
        The order of list members in resulting list is preserved: first all dictionaries from `self`,
        then all dictionaries from `other`.

        :param other: `Configuration` object OR list of project configurations to be added to `self`
        :return: new `Configuration` object, including all configurations from both `self` and `other` objects
        """
        list_other: List[Step] = other.configs if isinstance(other, Configuration) else other
        return Configuration(list.__add__(self.configs, list_other))

    def __mul__(self, other: Union['Configuration', int]) -> 'Configuration':
        """
        This functions defines operator ``*`` for :class:`Configuration` class objects.
        The resulting object is created by combining every `self` list member with
        every `other` list member using :func:`.combine()` function.

        :param other: `Configuration` object  OR an integer value to be multiplied to `self`
        :return: new `Configuration` object, consisting of the list of combined configurations
        """
        if isinstance(other, int):
            return Configuration(list.__mul__(self.configs, other))
        config_list: List[Step] = []
        for obj_a in self.configs:
            obj_a_copy = copy.deepcopy(obj_a)
            if obj_a.children:
                obj_a_copy.children = obj_a.children * other
            else:
                obj_a_copy.children = copy.deepcopy(other)

            config_list.append(obj_a_copy)
        return Configuration(config_list)

    def all(self) -> Iterable[Step]:
        """
        Function for configuration iterating.

        :return: iterable for all dictionary objects in :class:`Configuration` list
        """
        for obj_a in self.configs:
            if obj_a.children:
                for obj_b in obj_a.children.all():
                    yield obj_a + obj_b
            else:
                yield copy.deepcopy(obj_a)

    def dump(self, produce_string_command: bool = True) -> str:
        """
        Function for :class:`Configuration` objects pretty printing.

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

    def filter(self, checker: Callable[[Step], bool],
               parent: Step = None) -> 'Configuration':
        """
        This function is supposed to be called from main script, not configuration file.
        It uses provided `checker` to find all the configurations that pass the check,
        removing those not matching conditions.

        :param checker: a function that returns `True` if configuration passes the filter and `False` otherwise
        :param parent: an inner parameter for recursive usage; should be None when function is called from outside
        :return: new `Configuration` object without configurations not matching `checker` conditions
        """

        if parent is None:
            parent = Step()

        filtered_configs: Configuration = Configuration()

        for obj_a in self.configs:
            item: Step = parent + obj_a

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
                        obj_a_copy.children = Configuration(active_children_configs)
                    filtered_configs += [obj_a_copy]
            else:
                if checker(item):
                    filtered_configs += [copy.deepcopy(obj_a)]

        return filtered_configs


global_project_root = os.getcwd()


#: Variations is preserved as legacy alias for :class:`Configuration`
Variations = Configuration


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
