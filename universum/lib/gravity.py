from typing import cast, Any, Callable, ClassVar, Dict, Generic, List, NoReturn, Optional, Type, TypeVar

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

    def __getattribute__(self, item: Any) -> Any:  # TODO: narrow down type annotations
        cls: Type['Module'] = object.__getattribute__(self, "cls")
        main_settings = object.__getattribute__(self, "main_settings")
        for entry in cls.__mro__:
            try:
                settings: Any = getattr(main_settings, entry.__name__)  # TODO: narrow down type annotations
                return getattr(settings, item)
            except AttributeError:
                continue

        raise AttributeError("'" + cls.__name__ + "' object has no setting '" + item + "'")

    def __setattr__(self, key: Any, value: Any) -> None:  # TODO: narrow down type annotations
        cls: Type['Module'] = object.__getattribute__(self, "cls")
        main_settings: 'ModuleSettings' = object.__getattribute__(self, "main_settings")
        for entry in cls.__mro__:
            try:
                settings: Any = getattr(main_settings, entry.__name__)  # TODO: narrow down type annotations
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


T_Module = TypeVar('T_Module', bound='Module')

class Module(Generic[T_Module]):
    settings: ClassVar['Settings']
    main_settings: 'ModuleSettings'
    def __new__(klass: Type[T_Module], main_settings: 'ModuleSettings', *args, **kwargs) -> T_Module:
        instance: T_Module = super(Module, klass).__new__(klass)
        instance.main_settings = main_settings
        return instance


T = TypeVar('T', bound='Module')

def construct_component(klass: Type[T], main_settings: 'ModuleSettings', *args, **kwargs) -> T:
    if not getattr(main_settings, "active_modules", None):
        main_settings.active_modules = dict()

    if klass not in main_settings.active_modules:
        klass.settings = Settings(klass)
        instance: T = klass.__new__(klass, main_settings=main_settings)
        # https://github.com/python/mypy/blob/master/mypy/checkmember.py#180
        # Accessing __init__ in statically typed code would compromise
        # type safety unless used via super().
        instance.__init__(*args, **kwargs)  # type: ignore  
        main_settings.active_modules[klass] = instance
    return cast(T, main_settings.active_modules[klass])


T_Dependency = TypeVar('T_Dependency', bound='Module')

class Dependency(Generic[T_Dependency]):
    def __init__(self, klass: Type[T_Dependency]) -> None:
        self.klass = klass

    def __get__(self, instance: T_Dependency, owner: Any) -> Callable[..., T_Dependency]:
        def constructor_function(*args, **kwargs) -> T_Dependency:
            return construct_component(self.klass, instance.main_settings, *args, **kwargs)
        return constructor_function


def get_dependencies(klass: Type[Module], result: Optional[List[Type[Module]]]=None,
                     parent: Optional[Dict[Type[Module], Type[Module]]]=None) -> List[Type[Module]]:
    if result is None:
        result = list()
    if parent is None:
        parent = dict()

    result.append(klass)

    # parent classes
    all_dependenies: List[Module]
    all_dependencies = [x for x in klass.__mro__ if issubclass(x, Module) and x != Module and x != klass]
    # dependencies
    all_dependencies.extend([x.klass for x in klass.__dict__.values() if isinstance(x, Dependency)])

    for dependency in all_dependencies:
        parent[dependency] = klass

        if dependency not in result:
            get_dependencies(dependency, result, parent)

    return result


def define_arguments_recursive(klass, argument_parser):  # TODO: return here after ModuleArgumentParser is annotated
    modules = get_dependencies(klass)

    for current_module in modules:
        if "define_arguments" in current_module.__dict__:
            argument_parser.dest_prefix = current_module.__name__ + '.'
            current_module.define_arguments(argument_parser)

    argument_parser.dest_prefix = ''
