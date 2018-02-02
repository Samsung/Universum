import _universum.module_arguments


class ArgGroupWithDefault(_universum.module_arguments.ModuleArgumentGroup):
    def add_argument(self, *args, **kwargs):
        if "required" in kwargs and "default" not in kwargs:
            kwargs["required"] = False
            kwargs["default"] = ""

        super(ArgGroupWithDefault, self).add_argument(*args, **kwargs)


class ArgParserWithDefault(_universum.module_arguments.ModuleArgumentParser):
    def add_argument(self, *args, **kwargs):
        if "required" in kwargs and "default" not in kwargs:
            kwargs["required"] = False
            kwargs["default"] = ""

        super(ArgParserWithDefault, self).add_argument(*args, **kwargs)

    def add_argument_group(self, *args, **kwargs):
        group = super(ArgParserWithDefault, self).add_argument_group(*args, **kwargs)
        return ArgGroupWithDefault(group)
