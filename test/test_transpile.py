import unittest

from ..src.transpile import transpiled_function_object
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

import unittest

class TestTranspile(unittest.TestCase):

    def test_basic(self):
        a = basic_function()
        b = transpiled_function_object(basic_function, debug=True)()
        assert a == b

    def test_while(self):
        a=while_function()
        b=transpiled_function_object(while_function,debug=True)()
        assert a == b



if __name__ == '__main__':
    unittest.main()

