# Exprify

Remove the need for whitespace in Python code by converting it to expression-only syntax.

### Installation
Currently not on PyPi, so you'll need to install from source:
```bash
git clone git@github.com:juliusgeo/exprify.git
cd exprify
pip install .
```

### Usage
```python
from exprify import transpiled_function_ast
def readme_example_func():
    class A:
        def __init__(self, a):
            self.a = a
        def __add__(self, other):
            return self.a + other.a
    a = A(1)
    b = A(2)
    return a+b
print(transpiled_function_ast(readme_example_func))
# Output:
>>> readme_example_func = lambda: [(A := type('A', (), {'__init__': lambda self, a: setattr(self, 'a', a), '__add__': lambda self, other: self.a + other.a})), (a := A(1)), (b := A(2)), a + b][-1]
```

### Background

Because whitespace in Python has syntactic meaning, it is relatively difficult to obfuscate/minify Python code.
However, Python *expressions* don't have this same limitation. Unfortunately, writing a Python program that only uses expressions
is difficult (but not impossible), and results in code that is very difficult to refactor.
For example, compare the two following equivalent functions:
```python
def sum(a, b):
    f = a+b
    return f

sum = lambda a, b: a+b
```
The first necessarily requires whitespace--you will get a syntax error if the indentation is omitted. The second is a single line,
but can be difficult to read for complex examples. Let's look at one of those complex examples:
```python

def func_with_imports():
    import itertools
    from functools import reduce

    x = 0
    s = 0
    while x < 15:
        x = x + len(list(itertools.accumulate([1, 2, 3])))
        s += x + reduce(lambda a, b: a + b, [1, 2, 3])
    return s


func_with_imports = lambda: (((itertools := __import__('itertools')),), ((reduce := getattr(__import__('functools'), 'reduce')),), (x := 0), (s := 0), [((x := (x + len(list(itertools.accumulate([1, 2, 3]))))), (s := (s + (x + reduce(lambda a, b: a + b, [1, 2, 3])))))[-1] for _ in iter(lambda: x < 15, False)], s)[-1]

```
You can see now why it might be preferable to write in the first form, rather than the second, and have a computer translate it for you.

For my [previous obfuscated projects](https://gist.github.com/juliusgeo/0eb005a67f4b772b2b2b8ef54e00b509), I would do this conversion by hand, and then
use my [other project](https://github.com/juliusgeo/pyflate) which re-flows code written in the expression syntax into ASCII art to produce the final result.
This project is the missing link in the middle, hopefully allowing for a pipeline that transforms Python code from normal syntax -> expression only syntax -> minified or obfuscated result.

### Limitations

- Does not support error handling
- Does not support `async`
