# pylint: disable = redefined-outer-name, invalid-name

from argparse import ArgumentError
from unittest import mock
import pytest

from universum.lib.gravity import construct_component, define_arguments_recursive, Dependency
from universum.lib.gravity import get_dependencies
import universum.lib.module_arguments
import universum.lib.gravity


@pytest.fixture()
def mock_module():
    class MockedModule:
        def __new__(cls, *args, **kwargs):
            return old_module.__new__(cls, *args, **kwargs)

    old_module = universum.lib.gravity.Module
    universum.lib.gravity.Module = MockedModule

    yield MockedModule

    universum.lib.gravity.Module = old_module


def mock_define_arguments(klass):
    patcher = mock.patch.object(klass, "define_arguments", create=True)
    patcher.start()
    return klass


def test_dependencies_simple(mock_module):
    class OnlyDep(mock_module):
        pass

    class RootOneUser(mock_module):
        dep = Dependency(OnlyDep)

    assert get_dependencies(RootOneUser) == [RootOneUser, OnlyDep]
    assert get_dependencies(OnlyDep) == [OnlyDep]


def test_dependencies_two_users(mock_module):
    class Common(mock_module):
        pass

    class FirstDep(mock_module):
        dep = Dependency(Common)

    class SecondDep(mock_module):
        dep = Dependency(Common)

    class RootTwoUsers(mock_module):
        first = Dependency(FirstDep)
        second = Dependency(SecondDep)

    dependencies = get_dependencies(RootTwoUsers)
    for x in (RootTwoUsers, FirstDep, SecondDep, Common):
        assert x in dependencies


def test_define_arguments_mock_no_call(mock_module):
    @mock_define_arguments
    class FirstDependency(mock_module):
        pass

    @mock_define_arguments
    class NotADependency(mock_module):
        pass

    class RootDefineArgs(mock_module):
        dep = Dependency(FirstDependency)

    FirstDependency.define_arguments.assert_not_called()
    NotADependency.define_arguments.assert_not_called()

    parser = mock.MagicMock()
    define_arguments_recursive(RootDefineArgs, parser)

    assert parser.dest_prefix == ""
    FirstDependency.define_arguments.assert_called_with(parser)
    NotADependency.define_arguments.assert_not_called()


def test_define_arguments_3(mock_module):
    class ChainEnd(mock_module):
        @staticmethod
        def define_arguments(parser):
            group_parser = parser.get_or_create_group("ChainEnd group")
            group_parser.add_argument('--option3')

    class ChainSecond(mock_module):
        dep = Dependency(ChainEnd)

        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--option2')

    class ChainStart(mock_module):
        dep = Dependency(ChainSecond)

        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--option1')

    parser = universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(ChainStart, parser)
    settings = parser.parse_args(["--option2=abc"])
    assert settings.ChainStart.option1 is None
    assert settings.ChainSecond.option2 == "abc"
    assert settings.ChainEnd.option3 is None

    parser = universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(ChainSecond, parser)
    settings = parser.parse_args(["--option2=def"])
    assert 'ChainStart' not in dir(settings)
    assert settings.ChainSecond.option2 == "def"
    assert settings.ChainEnd.option3 is None

    parser = universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(ChainEnd, parser)
    settings = parser.parse_args([])
    assert 'ChainStart' not in dir(settings)
    assert 'ChainSecond' not in dir(settings)
    assert settings.ChainEnd.option3 is None


def test_define_arguments_inheritance(mock_module, capsys):
    class ParentModule(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--parent')

    class InheritedModule1(ParentModule):
        pass

    class InheritedModule2(ParentModule):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--child')

    class WrongInheritedModule(ParentModule):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--parent')

    parser = universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(ParentModule, parser)
    settings = parser.parse_args(["--parent=abc"])
    assert settings.ParentModule.parent == "abc"
    with pytest.raises(SystemExit) as exception_info:
        parser.parse_args(["--child=def"])
    assert exception_info.value.code == 2
    assert "unrecognized arguments: --child=def" in capsys.readouterr()[1]

    parser = universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(InheritedModule1, parser)
    settings = parser.parse_args(["--parent=abc"])
    assert settings.ParentModule.parent == "abc"

    parser = universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(InheritedModule2, parser)
    settings = parser.parse_args(["--parent=abc", "--child=def"])
    assert settings.ParentModule.parent == "abc"
    assert settings.InheritedModule2.child == "def"

    parser = universum.lib.module_arguments.ModuleArgumentParser()
    with pytest.raises(ArgumentError) as exception_info:
        define_arguments_recursive(WrongInheritedModule, parser)
    assert "conflicting option string: --parent" in str(exception_info.value)


def test_settings_access(mock_module):
    class S(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--option')

    class R(mock_module):
        dep = Dependency(S)

        def __init__(self):
            self.s = self.dep()

    settings = universum.lib.module_arguments.ModuleNamespace()
    child_settings = universum.lib.module_arguments.ModuleNamespace()
    child_settings.option = "abc"
    setattr(settings, 'S', child_settings)
    r = construct_component(R, settings)

    # get existing settings
    assert r.s.settings.option == "abc"

    # get non-existing settings
    with pytest.raises(AttributeError) as exception_info:
        print(r.settings.option)
    assert "'R' object has no setting 'option'" in str(exception_info.value)

    # get non-existing option
    with pytest.raises(AttributeError) as exception_info:
        print(r.s.settings.another_option)
    assert "'S' object has no setting 'another_option'" in str(exception_info.value)

    # set non-existing option
    with pytest.raises(AttributeError) as exception_info:
        r.s.settings.another_option = "def"
    assert "'S' object has no setting 'another_option'" in str(exception_info.value)

    # set non-existing settings
    with pytest.raises(AttributeError) as exception_info:
        r.settings.option = "hij"
    assert "'R' object has no setting 'option'" in str(exception_info.value)


def make_settings(name, value):
    settings = universum.lib.module_arguments.ModuleNamespace()
    child_settings = universum.lib.module_arguments.ModuleNamespace()
    child_settings.option = value

    if not isinstance(name, str):
        name = name.__name__
    setattr(settings, name, child_settings)
    return settings


def test_construct_component(mock_module):
    class Q(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--option')

        def __init__(self):
            self.member = self.settings.option

        def empty_init(self):
            pass

    class P(mock_module):
        dep = Dependency(Q)

        def __init__(self):
            self.q = 123

        def init_with_dependency(self):
            self.q = self.dep()

    # no reference to Q
    p1 = construct_component(P, make_settings(Q, ""))
    assert p1.q == 123

    # create dynamic reference to Q by calling method
    p2 = construct_component(P, make_settings(Q, "def"))
    p2.init_with_dependency()
    assert p2.q.member == "def"

    # create static reference to Q by rewriting __init__
    P.__init__ = P.init_with_dependency
    p3 = construct_component(P, make_settings(Q, "ghi"))
    assert p3.q.member == "ghi"

    # remove __init__ of Q to make sure "member" is present because of __init__ call
    Q.__init__ = Q.empty_init
    p4 = construct_component(P, make_settings(Q, "jkl"))
    assert 'member' not in dir(p4.q)


def test_construct_component_same_instance(mock_module):
    class V(mock_module):
        pass

    class U(mock_module):
        dep = Dependency(V)

        def __init__(self):
            self.v = self.dep()

    class T(mock_module):
        dep1 = Dependency(U)
        dep2 = Dependency(V)

        def __init__(self):
            self.u = self.dep1()
            self.v = self.dep2()

    settings = universum.lib.module_arguments.ModuleNamespace()
    t = construct_component(T, settings)
    assert t.v == t.u.v
    assert "T" in repr(t)
    assert "U" in repr(t.u)
    assert "V" in repr(t.v)

    u = construct_component(U, settings)
    assert t.u == u

    v = construct_component(V, settings)
    assert t.v == v


def test_construct_component_same_name(mock_module):

    def get_class(parameter):
        class TheOnlyClass(mock_module):
            the_only_parameter = parameter

        return TheOnlyClass

    settings = universum.lib.module_arguments.ModuleNamespace()
    first_object = construct_component(get_class("abc"), settings)
    second_object = construct_component(get_class("def"), settings)

    assert first_object.the_only_parameter == "abc"
    assert second_object.the_only_parameter == "def"


def test_additional_init_parameters(mock_module):
    class W(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--option')

        def __init__(self, param, named_parm):
            self.member1 = self.settings.option
            self.member2 = param
            self.member3 = named_parm

    class X(mock_module):
        dep = Dependency(W)

        def __init__(self):
            self.w = self.dep(123, named_parm=456)

    x = construct_component(X, make_settings(W, "abc"))
    assert x.w.member1 == "abc"
    assert x.w.member2 == 123
    assert x.w.member3 == 456


def parse_settings(klass, arguments):
    parser = universum.lib.module_arguments.ModuleArgumentParser()
    define_arguments_recursive(klass, parser)
    return parser.parse_args(arguments)


def test_construct_component_inheritance(mock_module):
    class BaseModule(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--base_option')

        def __init__(self, base_param, **kwargs):
            super().__init__(**kwargs)
            self.base_option = self.settings.base_option
            self.base_param = base_param

    class DerivedModule(BaseModule):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--derived_option')

        def __init__(self, **kwargs):
            super().__init__(456, **kwargs)
            self.derived_option = self.settings.derived_option
            self.derived_member = 123

    settings = parse_settings(DerivedModule, ["--base_option=abc", "--derived_option=def"])
    assert settings.BaseModule.base_option == "abc"
    assert settings.DerivedModule.derived_option == "def"
    derived = construct_component(DerivedModule, settings)
    assert derived.base_option == "abc"
    assert derived.derived_option == "def"
    assert derived.derived_member == 123
    assert derived.base_param == 456


def test_construct_component_multiple_inheritance(mock_module):
    class Base1(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--base1_option')

        def __init__(self, base1_param, **kwargs):
            super().__init__(**kwargs)
            self.base1_option = self.settings.base1_option
            self.base1_param = base1_param

    class Base2:
        def __init__(self, base2_param, **kwargs):
            super().__init__(**kwargs)
            self.base2_param = base2_param

    class Base3(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--base3_option')

        def __init__(self, base3_param, **kwargs):
            super().__init__(**kwargs)
            self.base3_option = self.settings.base3_option
            self.base3_param = base3_param

    class Base4(mock_module):
        def __init__(self, base4_param, **kwargs):
            super().__init__(**kwargs)
            self.base4_param = base4_param

    class DerivedMulti(Base1, Base2, Base3, Base4):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--derived_option')

        def __init__(self, **kwargs):
            super().__init__(base1_param="ab",
                                               base2_param="cd",
                                               base3_param="ef",
                                               base4_param="gh",
                                               **kwargs)
            self.derived_option = self.settings.derived_option
            self.derived_member = 123

    local_settings = parse_settings(DerivedMulti, ["--base1_option=abc", "--base3_option=def", "--derived_option=ghi"])
    derived = construct_component(DerivedMulti, local_settings)
    assert derived.derived_option == "ghi"
    assert derived.base1_option == "abc"
    assert derived.base3_option == "def"
    assert derived.base1_param == "ab"
    assert derived.base2_param == "cd"
    assert derived.base3_param == "ef"
    assert derived.base4_param == "gh"


def test_construct_component_multiple_instance(mock_module):
    class Z(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--zparam')

    class W(mock_module):
        dep = Dependency(Z)

        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--wparam')

        def __init__(self):
            super().__init__()
            if self.settings.wparam == "z":
                self.z = self.dep()
            else:
                self.nz = self.dep()

    settings1 = parse_settings(W, ["--wparam=z", "--zparam=abc"])
    w1 = construct_component(W, settings1)

    settings2 = parse_settings(W, ["--wparam=not_z", "--zparam=def"])
    w2 = construct_component(W, settings2)

    assert w1.settings.wparam == "z"
    assert w2.settings.wparam == "not_z"

    assert w1.z.settings.zparam == "abc"
    assert w2.nz.settings.zparam == "def"

    with pytest.raises(AttributeError) as exception_info:
        print(w1.nz.settings.zparam)
    assert "'W' object has no attribute 'nz'" in str(exception_info.value)

    with pytest.raises(AttributeError) as exception_info:
        print(w2.z.settings.zparam)
    assert "'W' object has no attribute 'z'" in str(exception_info.value)

    w1.settings.wparam = "new_value"
    assert w1.settings.wparam == "new_value"
    assert w2.settings.wparam == "not_z"


def test_settings_access_multiple_inheritance(mock_module):
    class BaseOne(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--baseone')

        def set_baseone(self, value):
            self.settings.baseone = value

    class BaseTwo(mock_module):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--basetwo')

        def set_derived(self, value):
            self.settings.derived = value

    class Derived(BaseOne, BaseTwo):
        @staticmethod
        def define_arguments(parser):
            parser.add_argument('--derived')

    local_settings = parse_settings(Derived, ["--baseone=abc", "--basetwo=def", "--derived=ghi"])
    b1 = construct_component(BaseOne, local_settings)
    b2 = construct_component(BaseTwo, local_settings)
    d = construct_component(Derived, local_settings)
    assert d.settings.derived == "ghi"
    assert d.settings.baseone == "abc"
    assert d.settings.basetwo == "def"
    assert b1.settings.baseone == "abc"
    assert b2.settings.basetwo == "def"

    with pytest.raises(AttributeError) as exception_info:
        print(b1.settings.derived)
    assert "'BaseOne' object has no setting 'derived'" in str(exception_info.value)

    with pytest.raises(AttributeError) as exception_info:
        print(b2.settings.baseone)
    assert "'BaseTwo' object has no setting 'baseone'" in str(exception_info.value)

    b1.settings.baseone = "zyx"
    assert d.settings.baseone == "zyx"

    d.settings.basetwo = "lmn"
    assert b2.settings.basetwo == "lmn"

    d.set_baseone("value1")
    assert d.settings.baseone == "value1"

    d.set_derived("value2")
    assert d.settings.derived == "value2"

    with pytest.raises(AttributeError) as exception_info:
        b2.set_derived("value4")
    assert "'BaseTwo' object has no setting 'derived'" in str(exception_info.value)
