Exprify
=======

Convert Python functions that use statements, to only using expressions.

Background
----------

Because whitespace in Python has syntactic meaning, it is relatively difficult to obfuscate/minify Python code.
However, Python *expressions* don't have this same limitation. Unfortunately, writing a Python program that only uses expressions
is difficult (but not impossible), and results in code that is very difficult to refactor.
For example, compare the two following equivalent functions:
```python
def sum(a, b):
    return a+b

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

Limitations
-----------

- Does not support error handling
- Functions which return `None` implicitly need to have an explicit `return None`
- Does not support `async`
- Does not support context managers
