# Exprify

Convert arbitrary Python code to expression-only syntax while preserving semantics.
Additionally includes functions for reflowing the expression-only code into arbitrary shapes (useful for creating ASCII art of your code).

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
If you want to turn a snippet into ASCII art, it will probably require some fine-tuning of the parameters to get an aesthetically pleasing result:

```python
from exprify import reflow
script = """
def pow(a, ex):
    ret = a
    while ex > 1:
        ret *= a
        ex -= 1
    return ret
    """
outline = """
8888888888888
8888888888888
8888
8888
888888888888
888888888888
8888
8888
8888888888888
8888888888888
"""
reflowed_script=reflow(script,outline, tolerance=1)
print(reflowed_script)
# Output:
);\
    pow=lambda a,\
    ex:[(A:=a),[[\
    (A:=\
    (A*a\
    )),(ex:=(ex-\
    1))][-1]for _\
    in iter\
    (lambda\
    :ex>1,False)]\
    ,A][-1];#####
```
### Background

Because whitespace in Python has syntactic meaning, it is relatively difficult to obfuscate/minify Python code.
However, Python *expressions* don't have this same limitation. Unfortunately, writing a Python program that only uses expressions
is difficult (but not impossible), and results in code that is very difficult to refactor.
For example, compare the two following equivalent functions:
```python
def pow(a, b):
    ret = a
    while b > 1:
        ret *= a
        b -= 1
    return ret

pow = lambda a, b: [(ret := a), [[(ret := (ret * a)), (b := (b - 1))][-1] for _ in iter(lambda: b > 1, False)], ret][-1]
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
This project automates the first step, and improves the ASCII art reflowing.


### How it works

#### Transpilation

Most of the tricks used here are described in a [wonderful article](https://qiita.com/KTakahiro1729/items/c9cb757473de50652374) by KTakahiro1729 (in Japanese).
This package automates the process of conversion, and introduces a few new tricks for other language constructs.

`while` loops are converted into list comprehensions with a hacky use of `iter` to control the loop.
```python
x = 0
while x < 5:
    x += 1
```
Is converted to:
```python
(x:=0, [(x:=x+1) for _ in iter(lambda: x < 5, False)])
```
The lambda function calculates the condition, and the iter continues to produce True until the sentinel value (2nd argument) is encountered.

`with` statements are converted very similarly to any other block of statements, but calls to `__enter__` and `__exit__` are added before and after the body, with additional NamedExpressions if the context managers are bound to variables.

##### Creating ASCII art

The `reflow` function takes a path to a script, and a path to a template file.
The script is first minified using [python-minifier](https://github.com/dflook/python-minifier). `python-minifier` renames
variables, and removes unneeded elements from the script, but does not change the structure of the code.
The minified code will still be reliant on whitespace, so it has to be transpiled before being reflowed.
The template file can be any kind of ASCII art, but must contain enough non-whitespace chars
to accommodate all the characters in the script after minification+transpilation.
The reflowing algorithm is a simple greedy algorithm that tries to fit as many tokens as possible within each section of the ascii art.
Each line of the template is separated into whitespace and non-whitespace sections, and the non-whitespace sections are filled with tokens from the script.
In cases where there is not enough room in a section to accommodate the next token, the token is either moved to the next section, or, if it is a name or a string, will be split into multiple tokens if possible.


### Limitations

- Does not support error handling
- Does not support `async`
- Does not support statements like `yield`, `break`, `del`, `continue`
