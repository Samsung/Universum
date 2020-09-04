from typing import cast, Any, Callable, ClassVar, Dict, Generic, List, Optional, Type, TypeVar, Union

from typing_extensions import Protocol

__all__ = [
    "Module",
    "Dependency",
    "construct_component",
    "define_arguments_recursive"
]


class ModuleSettings:
    def __init__(self, cls, main_settings) -> None:
        object.__setattr__(self, "cls", cls)
        object.__setattr__(self, "main_settings", main_settings)

    def __getattribute__(self, item):
        cls = object.__getattribute__(self, "cls")
        main_settings = object.__getattribute__(self, "main_settings")
        for entry in cls.__mro__:
            try:
                settings = getattr(main_settings, entry.__name__)
                return getattr(settings, item)
            except AttributeError:
                continue

        raise AttributeError("'" + cls.__name__ + "' object has no setting '" + item + "'")

    def __setattr__(self, key, value):
        cls = object.__getattribute__(self, "cls")
        main_settings = object.__getattribute__(self, "main_settings")
        for entry in cls.__mro__:
            try:
                settings = getattr(main_settings, entry.__name__)
                getattr(settings, key)
                setattr(settings, key, value)
                return
            except AttributeError:
                continue

        raise AttributeError("'" + cls.__name__ + "' object has no setting '" + key + "'")


class Settings:
    def __init__(self, cls: Type['Module']) -> None:
        self.cls: Type['Module'] = cls

    def __get__(self, obj: 'Module', objtype: Any = None) -> 'ModuleSettings':
        return ModuleSettings(self.cls, obj.main_settings)

    def __set__(self, obj: 'Module', settings: 'Settings'):
        setattr(obj.main_settings, self.cls.__name__, settings)


class HasModulesMapping(Protocol):
    active_modules: Dict[Type['Module'], 'Module']


class Module:
    settings: ClassVar['Settings']
    main_settings: 'HasModulesMapping'

    def __init__(self, *args, **kwargs):  # workaround for type checking
        pass

    def __new__(cls: Type['Module'], main_settings: 'HasModulesMapping', *args, **kwargs) -> 'Module':
        instance: 'Module' = super(Module, cls).__new__(cls)
        instance.main_settings = main_settings
        return instance


ComponentType = TypeVar('ComponentType', bound=Module)


def construct_component(cls: Type[ComponentType], main_settings: 'HasModulesMapping', *args, **kwargs) -> ComponentType:
    if not getattr(main_settings, "active_modules", None):
        main_settings.active_modules = dict()

    if cls not in main_settings.active_modules:
        cls.settings = Settings(cls)
        instance: 'Module' = cls.__new__(cls, main_settings=main_settings)
        # https://github.com/python/mypy/blob/master/mypy/checkmember.py#180
        # Accessing __init__ in statically typed code would compromise
        # type safety unless used via super().
        # noinspection PyArgumentList
        instance.__init__(*args, **kwargs)  # type: ignore
        main_settings.active_modules[cls] = instance
    return cast(ComponentType, main_settings.active_modules[cls])


DependencyType = TypeVar('DependencyType', bound=Module)


class Dependency(Generic[DependencyType]):
    def __init__(self, cls: Type[DependencyType]) -> None:
        self.cls = cls

    # The source and the target of the dependency are different modules,
    # so we need to use different type variables to annotate them.
    # instance parameter of the __get__ method is source module.
    def __get__(self, instance: Module, owner: Any) -> Callable[..., DependencyType]:
        def constructor_function(*args, **kwargs) -> DependencyType:
            return construct_component(self.cls, instance.main_settings, *args, **kwargs)
        return constructor_function


def get_dependencies(cls: Type[Module], result: Optional[List[Type[Module]]] = None) -> List[Type[Module]]:
    if result is None:
        result = list()

    result.append(cls)

    # parent classes
    all_dependencies: List[Type[Module]]
    all_dependencies = [x for x in cls.__mro__ if issubclass(x, Module) and x != Module and x != cls]
    # dependencies
    all_dependencies.extend([x.cls for x in cls.__dict__.values() if isinstance(x, Dependency)])

    for dependency in all_dependencies:
        if dependency not in result:
            get_dependencies(dependency, result)

    return result


def define_arguments_recursive(cls, argument_parser):  # TODO: return here after ModuleArgumentParser is annotated
    modules = get_dependencies(cls)

    for current_module in modules:
        if "define_arguments" in current_module.__dict__:
            argument_parser.dest_prefix = current_module.__name__ + '.'
            # noinspection PyUnresolvedReferences
            current_module.define_arguments(argument_parser)

    argument_parser.dest_prefix = ''
