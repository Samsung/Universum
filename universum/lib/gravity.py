from typing import cast, Any, Callable, ClassVar, Dict, Generic, List, NoReturn, Optional, Type, TypeVar, Union

__all__ = [
    "Module",
    "Dependency",
    "construct_component",
    "define_arguments_recursive"
]


class ModuleSettings:
    def __init__(self, cls: Type['Module'], main_settings: 'ModuleSettings') -> None:
        object.__setattr__(self, "cls", cls)
        object.__setattr__(self, "main_settings", main_settings)
        # TODO: can't clarify that active_modules[Type[X]] returns X (https://github.com/python/mypy/issues/4928)
        self.active_modules: Optional[Dict[Type[Module], Module]]

    def __getattribute__(self, item: str) -> Union[str, List[str]]:
        cls: Type['Module'] = object.__getattribute__(self, "cls")
        main_settings = object.__getattribute__(self, "main_settings")
        for entry in cls.__mro__:
            try:
                settings: 'Settings' = getattr(main_settings, entry.__name__)
                return getattr(settings, item)
            except AttributeError:
                continue

        raise AttributeError("'" + cls.__name__ + "' object has no setting '" + item + "'")

    def __setattr__(self, key: str, value: Union[str, List[str]]) -> None:
        cls: Type['Module'] = object.__getattribute__(self, "cls")
        main_settings: 'ModuleSettings' = object.__getattribute__(self, "main_settings")
        for entry in cls.__mro__:
            try:
                settings: 'Settings' = getattr(main_settings, entry.__name__)
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


ModuleType = TypeVar('ModuleType', bound='Module')

class Module(Generic[ModuleType]):
    settings: ClassVar['Settings']
    main_settings: 'ModuleSettings'
    def __new__(cls: Type[ModuleType], main_settings: 'ModuleSettings', *args, **kwargs) -> ModuleType:
        instance: ModuleType = super(Module, cls).__new__(cls)
        instance.main_settings = main_settings
        return instance


ComponentType = TypeVar('ComponentType', bound='Module')

def construct_component(cls: Type[ComponentType], main_settings: 'ModuleSettings', *args, **kwargs) -> ComponentType:
    if not getattr(main_settings, "active_modules", None):
        main_settings.active_modules = dict()

    if cls not in main_settings.active_modules:
        cls.settings = Settings(cls)
        instance: ComponentType = cls.__new__(cls, main_settings=main_settings)
        # https://github.com/python/mypy/blob/master/mypy/checkmember.py#180
        # Accessing __init__ in statically typed code would compromise
        # type safety unless used via super().
        instance.__init__(*args, **kwargs)  # type: ignore
        main_settings.active_modules[cls] = instance
    return cast(ComponentType, main_settings.active_modules[cls])


DependencyType = TypeVar('DependencyType', bound='Module')

class Dependency(Generic[DependencyType]):
    def __init__(self, cls: Type[DependencyType]) -> None:
        self.cls = cls

    def __get__(self, instance: DependencyType, owner: Any) -> Callable[..., DependencyType]:
        def constructor_function(*args, **kwargs) -> DependencyType:
            return construct_component(self.cls, instance.main_settings, *args, **kwargs)
        return constructor_function


def get_dependencies(cls: Type[Module], result: Optional[List[Type[Module]]] = None,
                     parent: Optional[Dict[Type[Module], Type[Module]]] = None) -> List[Type[Module]]:
    if result is None:
        result = list()
    if parent is None:
        parent = dict()

    result.append(cls)

    # parent classes
    all_dependencies: List[Type[Module]]
    all_dependencies = [x for x in cls.__mro__ if issubclass(x, Module) and x != Module and x != cls]
    # dependencies
    all_dependencies.extend([x.cls for x in cls.__dict__.values() if isinstance(x, Dependency)])

    for dependency in all_dependencies:
        parent[dependency] = cls

        if dependency not in result:
            get_dependencies(dependency, result, parent)

    return result


def define_arguments_recursive(cls, argument_parser):  # TODO: return here after ModuleArgumentParser is annotated
    modules = get_dependencies(cls)

    for current_module in modules:
        if "define_arguments" in current_module.__dict__:
            argument_parser.dest_prefix = current_module.__name__ + '.'
            current_module.define_arguments(argument_parser)

    argument_parser.dest_prefix = ''
