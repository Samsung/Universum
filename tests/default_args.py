import universum.lib.module_arguments


class ArgGroupWithDefault(universum.lib.module_arguments.ModuleArgumentGroup):
    def add_argument(self, *args, **kwargs):
        if "required" in kwargs and "default" not in kwargs:
            kwargs["required"] = False
            kwargs["default"] = ""

        super().add_argument(*args, **kwargs)


class ArgParserWithDefault(universum.lib.module_arguments.ModuleArgumentParser):
    def add_argument(self, *args, **kwargs):
        if "required" in kwargs and "default" not in kwargs:
            kwargs["required"] = False
            kwargs["default"] = ""

        super().add_argument(*args, **kwargs)

    def add_argument_group(self, *args, **kwargs):
        group = super().add_argument_group(*args, **kwargs)
        return ArgGroupWithDefault(group)
