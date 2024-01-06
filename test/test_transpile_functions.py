import pytest

from exprify import transpiled_function_object
from exprify.ast_transformer import ExprifyException


def basic_func():
    x = 0
    for i in range(10):
        if x < 5:
            x += 1
        elif x > 2:
            x += 2
        elif x > 3:
            x += 3
        else:
            x = 0
    return x


def while_func():
    x = 0
    while x < 15:
        if x < 5:
            x += 1
        elif x > 2:
            x += 2
        elif x > 3:
            x += 3
        else:
            x = 0
    return x


def nested_func():
    def sum(a, b, c=1):
        def add1(b):
            return b + 1

        return a + add1(b) + c

    x = 0
    s = 0
    while x < 15:
        x = sum(x, 3, c=2)
        s = sum(s, x)
    return s


def imports_func():
    import itertools
    from functools import reduce

    x = 0
    s = 0
    while x < 15:
        x = x + len(list(itertools.accumulate([1, 2, 3])))
        s += x + reduce(lambda a, b: a + b, [1, 2, 3])
    return s


def class_func():
    class A:
        x = y = 0

        def __init__(self, x):
            self.x = x

        def add(self):
            self.x += 1
            self.y = self.x

    x = A(0)
    for i in range(10):
        x.add()
    return x.x


def multiple_returns_func(a):
    if a > 0:
        return a
    elif a < 0:
        return abs(a)
    else:
        return 0


def tuple_unpacking_func():
    x, y = 0, 1
    for i, j in zip(range(10), range(20)):
        x += i
        y += j
    return x, y


def readme_example_func():
    class A:
        def __init__(self, a):
            self.a = a

        def __add__(self, other):
            return self.a + other.a

    a = A(1)
    b = A(2)
    return a + b


def recursive_func():
    def f(x):
        if x > 0:
            return f(x - 1)
        else:
            return 0

    return f(10)


def context_manager_func():
    with open("test_scripts/zipy.py") as f, open("test_scripts/zipy.py") as g:
        return f.read() + str(len(g.readlines()))


@pytest.mark.parametrize(
    "func",
    [
        basic_func,
        while_func,
        nested_func,
        imports_func,
        class_func,
        tuple_unpacking_func,
        context_manager_func,
        readme_example_func,
        recursive_func,
    ],
)
def test_func_no_args(func):
    a = func()
    b = transpiled_function_object(func, debug=True)()
    assert a == b, f"{a} != {b}"


@pytest.mark.parametrize("func, args", [(multiple_returns_func, (1, -1, 0))])
def test_func_args(func, args):
    for arg in args:
        a = func(arg)
        b = transpiled_function_object(func, debug=True)(arg)
        assert a == b, f"{a} != {b}"


def continue_func():
    for _ in range(2):
        continue


def break_func():
    for _ in range(2):
        break


def yield_func():
    for _ in range(2):
        yield 1


def yield_from_func():
    for _ in range(2):
        yield from [1, 2]


def del_func():
    a = 1
    del a


def pass_func():
    pass


def try_func():
    try:
        raise Exception()
    except Exception:
        return None


def try_star_func():
    try:
        raise Exception()
    except* Exception:
        None


def async_func():
    async def a():
        return 1


def async_for_func():
    async def a():
        async for _ in range(2):
            return


def async_with_func():
    async def a():
        async with True:
            return


@pytest.mark.parametrize(
    "func",
    [
        continue_func,
        break_func,
        yield_func,
        yield_from_func,
        del_func,
        pass_func,
        try_func,
        try_star_func,
        async_func,
        async_for_func,
        async_with_func,
    ],
)
def test_failure_funcs(func):
    with pytest.raises(ExprifyException):
        transpiled_function_object(func, debug=True)
