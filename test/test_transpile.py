from ..src.transpile import transpiled_function_object
import unittest


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


class TestTranspile(unittest.TestCase):
    def test_basic(self):
        a = basic_function()
        b = transpiled_function_object(basic_function, debug=True)()
        assert a == b, f"{a} != {b}"

    def test_while(self):
        a = while_function()
        b = transpiled_function_object(while_function, debug=True)()
        assert a == b, f"{a} != {b}"

    def test_nested(self):
        a = nested_func()
        b = transpiled_function_object(nested_func, debug=True)()
        assert a == b, f"{a} != {b}"

    def test_imports(self):
        a = func_with_imports()
        b = transpiled_function_object(func_with_imports, debug=True)()
        assert a == b, f"{a} != {b}"

    def test_class(self):
        a = class_func()
        b = transpiled_function_object(class_func, debug=True)()
        assert a == b, f"{a} != {b}"

    def test_multiple_returns(self):
        a = multiple_returns(1)
        b = transpiled_function_object(multiple_returns, debug=True)(1)
        assert a == b, f"{a} != {b}"
        a = multiple_returns(-1)
        b = transpiled_function_object(multiple_returns, debug=True)(-1)
        assert a == b, f"{a} != {b}"
        a = multiple_returns(0)
        b = transpiled_function_object(multiple_returns, debug=True)(0)
        assert a == b, f"{a} != {b}"


if __name__ == "__main__":
    unittest.main()
