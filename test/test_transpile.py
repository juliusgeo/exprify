from exprify import transpiled_function_object
import pytest


def basic_function():
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


def while_function():
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
    def sum(a, b):
        def add1(b):
            return b + 1

        return a + add1(b)

    x = 0
    s = 0
    while x < 15:
        x = sum(x, 3)
        s = sum(s, x)
    return s


def func_with_imports():
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
            return None

        def add(self):
            self.x += 1

    x = A(0)
    for i in range(10):
        x.add()
    return x.x


def multiple_returns(a):
    if a > 0:
        return a
    elif a < 0:
        return abs(a)
    else:
        return 0


@pytest.mark.parametrize(
    "func", [basic_function, while_function, nested_func, func_with_imports, class_func]
)
def test_func_no_args(func):
    a = func()
    b = transpiled_function_object(func, debug=True)()
    assert a == b, f"{a} != {b}"


@pytest.mark.parametrize("func, args", [(multiple_returns, (1, -1, 0))])
def test_func_args(func, args):
    for arg in args:
        a = multiple_returns(arg)
        b = transpiled_function_object(multiple_returns, debug=True)(arg)
        assert a == b, f"{a} != {b}"
