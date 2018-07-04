# -*- coding: UTF-8 -*-

__all__ = [
    "Module",
    "Dependency",
    "construct_component",
    "define_arguments_recursive"
]


class Settings(object):
    def __get__(self, obj, objtype=None):
        settings = getattr(obj._main_settings, obj.__class__.__name__, None)
        if not settings:
            raise AttributeError("No settings available for module " + obj.__class__.__name__)
        return settings

    def __set__(self, obj, settings):
        setattr(obj._main_settings, obj.__class__.__name__, settings)


def get_string_name(name):
    if not isinstance(name, basestring):
        name = name.__name__
    return name


class Module(object):
    settings = Settings()

    def __new__(cls, main_settings=None, *args, **kwargs):
        instance = super(Module, cls).__new__(cls)
        if main_settings:
            instance._main_settings = main_settings
        return instance

    def __init__(self, *args, **kwargs):
        pass

    def add_settings(self, module_name):
        new_settings = getattr(self._main_settings, get_string_name(module_name), None)
        try:
            current_settings = self.settings
            for item in vars(new_settings):
                if not hasattr(current_settings, item):
                    setattr(current_settings, item, getattr(new_settings, item))
        except AttributeError:
            # current module has no own settings
            setattr(self._main_settings, self.__class__.__name__, new_settings)
        except TypeError:
            # 'module_name' module has no own settings
            return


def construct_component(name, main_settings, *args, **kwargs):
    if not getattr(main_settings, "name_to_module_map", None):
        main_settings.name_to_module_map = get_name_to_module_map()

    if not getattr(main_settings, "active_modules", None):
        main_settings.active_modules = dict()

    name = get_string_name(name)

    if name not in main_settings.active_modules:
        klass = main_settings.name_to_module_map[name]
        instance = klass.__new__(klass, main_settings=main_settings)
        instance.__init__(*args, **kwargs)
        main_settings.active_modules[name] = instance
    return main_settings.active_modules[name]


class Dependency(object):
    def __init__(self, name):
        self.name = get_string_name(name)

    def __get__(self, instance, owner):
        def constructor_function(*args, **kwargs):
            return construct_component(self.name, instance._main_settings, *args, **kwargs)

        return constructor_function


def get_name_to_module_map():
    result = {}
    stack = [Module]

    while stack:
        parent = stack.pop()
        for child in parent.__subclasses__():
            if child.__name__ not in result:
                result[child.__name__] = child
                stack.append(child)

    return result


def get_dependencies(klass, name_to_module_map, result=None, parent=None, stack=None):
    if result is None:
        result = list()
    if parent is None:
        parent = dict()
    if stack is None:
        stack = set()

    stack.add(klass)
    result.append(klass)

    # parent classes
    all_dependencies = [x for x in klass.__mro__ if issubclass(x, Module) and x != Module and x != klass]
    # dependencies
    all_dependencies.extend([name_to_module_map[x.name] for x in klass.__dict__.values() if isinstance(x, Dependency)])

    for dependency in all_dependencies:
        parent[dependency] = klass

        if dependency not in result:
            get_dependencies(dependency, name_to_module_map, result, parent, stack)
        elif dependency in stack:
            current = dependency
            cycle = [current.__name__]
            while True:
                current = parent[current]
                cycle += [current.__name__]
                if current == dependency:
                    break
            cycle.reverse()
            raise LookupError("Circular dependency detected, " + "->".join(cycle))

    stack.remove(klass)
    return result


def define_arguments_recursive(klass, argument_parser):
    name_to_module_map = get_name_to_module_map()
    modules = get_dependencies(klass, name_to_module_map)

    for current_module in modules:
        argument_parser.dest_prefix = current_module.__name__ + '.'
        try:
            current_module.define_arguments(argument_parser)
        except AttributeError:
            pass

    argument_parser.dest_prefix = ''
