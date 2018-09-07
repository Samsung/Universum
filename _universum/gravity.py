# -*- coding: UTF-8 -*-

__all__ = [
    "Module",
    "Dependency",
    "construct_component",
    "define_arguments_recursive"
]


class ModuleSettings(object):
    def __init__(self, cls, main_settings):
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


class Settings(object):
    def __init__(self, cls):
        self.cls = cls

    def __get__(self, obj, objtype=None):
        return ModuleSettings(self.cls, obj.main_settings)

    def __set__(self, obj, settings):
        setattr(obj.main_settings, self.cls.__name__, settings)


class Module(object):
    def __new__(cls, main_settings, *args, **kwargs):
        instance = super(Module, cls).__new__(cls)
        instance.main_settings = main_settings
        return instance


def construct_component(klass, main_settings, *args, **kwargs):
    if not getattr(main_settings, "active_modules", None):
        main_settings.active_modules = dict()

    if klass not in main_settings.active_modules:
        klass.settings = Settings(klass)
        instance = klass.__new__(klass, main_settings=main_settings)
        instance.__init__(*args, **kwargs)
        main_settings.active_modules[klass] = instance
    return main_settings.active_modules[klass]


class Dependency(object):
    def __init__(self, klass, *args, **kwargs):
        super(Dependency, self).__init__(*args, **kwargs)
        self.klass = klass

    def __get__(self, instance, owner):
        def constructor_function(*args, **kwargs):
            return construct_component(self.klass, instance.main_settings, *args, **kwargs)
        return constructor_function


def get_dependencies(klass, result=None, parent=None):
    if result is None:
        result = list()
    if parent is None:
        parent = dict()

    result.append(klass)

    # parent classes
    all_dependencies = [x for x in klass.__mro__ if issubclass(x, Module) and x != Module and x != klass]
    # dependencies
    all_dependencies.extend([x.klass for x in klass.__dict__.values() if isinstance(x, Dependency)])

    for dependency in all_dependencies:
        parent[dependency] = klass

        if dependency not in result:
            get_dependencies(dependency, result, parent)

    return result


def define_arguments_recursive(klass, argument_parser):
    modules = get_dependencies(klass)

    for current_module in modules:
        argument_parser.dest_prefix = current_module.__name__ + '.'
        try:
            current_module.define_arguments(argument_parser)
        except AttributeError:
            pass

    argument_parser.dest_prefix = ''
