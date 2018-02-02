__all__ = ["Module", "Dependency", "construct_component", "define_arguments_recursive"]


class Module(object):
    pass


def wrap_module(klass):
    # TODO: we do not support calls of parent class with regular super, which is not ok for
    # TODO: non-module classes participating in multiple inheritance
    # TODO: this could be fixed by changing wrapping using class with rewriting __init__
    # TODO: at construction time
    class Wrapped(klass):
        def __init__(self, main_settings, *args, **kwargs):
            self.main_settings = main_settings
            self.super_init(Wrapped, *args, **kwargs)

        def super_init(self, type1, *args, **kwargs):
            super_self = super(type1, self)
            super_name = self.__class__.__mro__[self.__class__.__mro__.index(type1) + 1].__name__
            type1_settings = getattr(self.main_settings, super_name, None)

            try:
                if type1_settings is not None:
                    super_self.__init__(type1_settings, *args, **kwargs)
                else:
                    super_self.__init__(*args, **kwargs)

            except TypeError, exc:
                if not getattr(exc, "already_processed", False):
                    # Modify exception message to add reference to object being constructed
                    exc.args = (exc.args[0] + ", super_self is instance of " + super_name,) + exc.args[1:]
                    # Do not modify the exception message twice, if one constructor calls another inside
                    exc.already_processed = True
                raise

        def __repr__(self):
            return "<Wrapped(" + klass.__module__ + "." + klass.__name__ + ") object at " + str(hex(id(self))) + " >"

    return Wrapped


def construct_component(name, main_settings, *args, **kwargs):
    if not getattr(main_settings, "name_to_module_map", None):
        main_settings.name_to_module_map = get_name_to_module_map()

    if not getattr(main_settings, "active_modules", None):
        main_settings.active_modules = dict()

    if not isinstance(name, basestring):
        name = name.__name__

    if name not in main_settings.active_modules:
        klass = wrap_module(main_settings.name_to_module_map[name])
        instance = klass(main_settings, *args, **kwargs)
        main_settings.active_modules[name] = instance
    return main_settings.active_modules[name]


class Dependency(object):
    def __init__(self, name):
        if not isinstance(name, basestring):
            name = name.__name__
        self.name = name

    def __get__(self, instance, owner):
        def constructor_function(*args, **kwargs):
            return construct_component(self.name, instance.main_settings, *args, **kwargs)

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
