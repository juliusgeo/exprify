# Exprify

Convert a subset of Python to expression-only syntax while preserving semantics.
Additionally includes functionality for reflowing the expression-only code into executable ASCII art.

![](https://github.com/juliusgeo/exprify/blob/master/demo.gif)

### Installation
Currently not on PyPi, so you'll need to install from source:
```bash
git clone git@github.com:juliusgeo/exprify.git
cd exprify
pip install .
# Install requirements
pip install -r requirements.txt
```

### Usage

This package provides a command-line utility for ease of use.

Transpile to expression-only syntax
```bash
exprify <your script>.py
```

Transpile, and then reflow to fit the ASCII art in `<your outline>.txt`
```bash
exprify <your script>.py -o <your outline>.txt
```
If you want to turn a snippet into ASCII art, it will probably require some fine-tuning of the parameters to get an aesthetically pleasing result.
Currently, the only parameter exposed is `tolerance`, which determines how closely the output must match the outline:

```bash
exprify <your script>.py -o <your outline>.txt -t 3
```

### Background

Because whitespace in Python has syntactic meaning, it is relatively difficult to obfuscate/minify Python code.
However, Python *expressions* don't have this same limitation. Unfortunately, writing a Python program that only uses expressions
is difficult (but not impossible), and results in code that is very difficult to refactor. I ran into this issue many times
while creating some of my [previous obfuscated projects](https://gist.github.com/juliusgeo/0eb005a67f4b772b2b2b8ef54e00b509).
Translating Python code to expression only syntax becomes very time consuming because I would inevitably introduce bugs,
and resolving them was quite difficult when looking at what is essentially a very long one-liner.
The process of converting the hand-transpiled code to ASCII art also required a *lot* of manual touch-ups,
despite automating part of the process with [pyflate](https://github.com/juliusgeo/pyflate) (which is now part of this project).

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


### How it works

#### Transpilation

Most of the tricks used here are described in a [wonderful article](https://qiita.com/KTakahiro1729/items/c9cb757473de50652374) by KTakahiro1729 (in Japanese).
This package automates the process of conversion, and introduces a few new tricks for other language constructs.

###### Functions

Functions are converted into lambda functions, where the body is a tuple containing NamedExpressions, or list comprehensions. Because a lambda function by default returns the entire expression,
if there is a return value that is appended to the end of the tuple, and it is wrapped in a subscript so that the return value is returned instead of the entire tuple.

###### Loops and blocks
`for` loops are probably the easiest to convert, as they map very cleanly to list comprehensions (as long as the limitations are not exceeded).
```python
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
basic_func = lambda: [(x := 0), [(x := (x + 1)) if x < 5
                                 else (x := (x + 2)) if x > 2
                                 else (x := (x + 3)) if x > 3
                                 else (x := 0) for i in range(10)], x][-1]
```
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
A block like this:
```python
def context_manager_func():
    with open("test_scripts/zipy.py") as f, open("test_scripts/zipy.py") as g:
        return f.read() + str(len(g.readlines()))
context_manager_func = lambda: ((f := getattr(open('test_scripts/zipy.py'), '__enter__')()),
                                (g := getattr(open('test_scripts/zipy.py'), '__enter__')()),
                                f.read() + str(len(g.readlines())),
                                getattr(open('test_scripts/zipy.py'), '__exit__')(),
                                getattr(open('test_scripts/zipy.py'), '__exit__')())[2]
```
Notice the subscript in this case is to elide the calls to `__enter__` and `__exit__` from the return value.

###### Classes
Classes are converted into a tuple containing a call to `type` and a dictionary of class attributes and methods.
Attributes are mutated using setattr, because you can't assign to a class attribute in a NamedExpression, but attribute access is the same.
```python
class A:
    x = y = 0

    def __init__(self, x):
        self.x = x

    def add(self):
        self.x += 1
        self.y = self.x

(A := type('A', (),
           {'x': 0, 'y': 0,
            '__init__': lambda self, x: setattr(self, 'x', x),
            'add': lambda self: [setattr(self, 'x', self.x + 1),
                                 setattr(self, 'y', self.x)][-1]}))
```

###### Tuple unpacking

You unfortunately cannot do tuple unpacking in named expressions. Something like `x,y:=1,2` will not work. So, instead we
just assign a temporary variable, and then assign each target in the unpacking to the temporary variable.
```python
def tuple_unpacking_func():
    x, y = 0, 1
    for i, j in zip(range(10), range(20)):
        x += i
        y += j
    return x, y

tuple_unpacking_func = lambda: [[(inter7 := (0, 1)),
                                 (x := inter7[0]),
                                 (y := inter7[1])],
                                [[(x := (x + i)), (y := (y + j))][-1] for i, j in zip(range(10), range(20))],
                                (x, y)][-1]
```

###### Exception handling

Exception handling is tricky using expressions only. First, you must abuse the `contextlib.ContextDecorator` class to create
an error handling class that looks like this:

```python
from contextlib import ContextDecorator
class capture_exceptions(ContextDecorator):
    def __init__(self, except_handlers={}, final=None, except_callable=None):
        self.except_handlers = except_handlers
        self.final = final

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.except_handlers.get(exc_type, None)
        self.final
        return exc_type in self.except_handlers
```

This uses a unique feature of context managers, which will call the `__exit__` function when they're done,
with some info on what exceptions happened during. Then, if you provide the exception types, and a corresponding expression
that assigns to an intermediate result, you can emulate the behavior of:

```python
try:
    return 1 + "1"
except TypeError:
    return "blah"
```
with:
```python
(capture_exceptions(except_handlers={Exception: (inter:= "blah")})(lambda: (inter := 1 + "1"))(), inter)
```
Which will work correctly! And, once you convert the `capture_exceptions` class to expression-only syntax and then
inject it at the beginning of the script, results in error handling code that doesn't need any indentation.

Throwing exceptions is similarly hacky, abusing the `.throw()` method of generators:
```python
(_ for _ in ()).throw(IndexError)
```


##### Creating ASCII art

The script is first minified using [python-minifier](https://github.com/dflook/python-minifier). `python-minifier` renames
variables, and removes unneeded elements from the script, but does not change the structure of the code.
The minified code will still be reliant on whitespace, so it has to be transpiled before being reflowed.
The template file can be any kind of ASCII art, but must contain enough non-whitespace chars
to accommodate all the characters in the script after minification+transpilation.
The reflowing algorithm is a simple greedy algorithm that tries to fit as many tokens as possible within each section of the ascii art.
Each line of the template is separated into whitespace and non-whitespace sections, and the non-whitespace sections are filled with tokens from the script.
In cases where there is not enough room in a section to accommodate the next token, the token is either moved to the next section, or, if it is a name or a string, will be split into multiple tokens if possible.
The `tolerance` parameter controls how much a token can overshoot the available space in a section before it is either split, or moved to the next section.

Here's an example of the reflowing algorithm on a complex script (the script is from the [zipyphus](https://github.com/juliusgeo/zipyphus) project):
```python
(
);                         J=range;G='sa'\
                       'mple.txt';F='sam'\
                    'ple.zip';B=bin;C='ascii'\
                  ;D=int;A=len;(K:=getattr(\
                 __import__('collect'  'ions'\
                 ),'namedtuple'))        ;(Union\
                 :=getattr(              \
                 __import__('ty'          'ping'\
                   ),'Union'))       ;((Q:=   \
                     __import__('b''inascii') )\
                      ,(E:=__import__        (''\
                      'struct')),(time       :=\
                        __import__(''   'time'\
                        )));(L:=getattr\
        (                __import__('funct'  'ools'\
        ),'par'             'tial'));(M:=   __import__(\
         'zipfile'           ));(N:=getattr(__import__('os'\
         ),'remove'            ));O=K('T''oken',['offset',''\
         'length'                 ,'indicator']);R=lambda input_string\
           ,max_offset            =2047,     max_length=31:[(B:=\
         input_string               ),(E:=[]),(D:=0),(B:=memoryview(B.encode\
         (  C))),(G:=               A(B)),[[[(inter1:=P(B[:D],B[D:],max_length\
         ,max_offset)             ),(F:=inter1[0]),(H:=inter1[1])],E.append\
          (O(H,F,B[D])           ),(   D:=(D+F))][-1]for _ in iter(lambda:D<G\
          ,False)],E][-         1];     P=lambda window,input_string,max_length\
        =31,max_offset         =4095      :[(D:=input_string),(C:=window),(E:=\
       A   (C)),[(inter2      :=(2,       0)),(B:=inter2[0]),(F:=inter2[1])],\
      (H:=D[0]),(I:=        L(S,C,D    ,A(D),E)),[[(inter3:=(G,K)),(B:=inter3\
       [0]),(F:=inter3     [1])]if  max_length>G>B else None for G,K in[(I(E-\
        A),A)for A in   J(1,min(E,max_offset)+1)if C[-A]==H]],(B,F)if B>2else\
      (1,0)][-1];S=    lambda window,input_string,i_len,w_len,start_idx:[(B:=\
      start_idx),(A:= 0),(C:=(w_len-B)),[(A:=(A+1))for _ in iter(lambda:A<i_len\
      and window[B+A %C]==input_string[A],False)],A][-1];T=lambda val:[(A:=val),\
      (A:=ord(A))if  isinstance(A   ,str)else None,(D(B(A+48),2),8)if A<144else\
      (D(B(A-144+400),2),9)if A<257  else(D(B(A-257+20),2),7)if A<280else(D(B\
      (A-280+192),2),8)if A<288else   None][-1];U=lambda n:[(n,0,0)if n<=2else\
       None,(254+n,0,0)if n<=10else    (265+(n-11)//2,(n-11)%2,1)if n<=18else\
       (269+(n-19)//4,(n-19)%4,2)if    n<=34else(273+(n-35)//8,(n-35)%8,3)if n\
         <=66else(277+(n-67)//16,(      n-67)%16,4)if n<=130else(281+(n-131)//\
          32,(n-131)%32,5)if n<258      else(285,0,0)if n==258else None][-1];\
           V=lambda n :(n-1,0,0)if      n<=4else((n-5)//2+4,n-5,1)if n<=8else\
            ((n-9)//4 +6,n-9,2)if n     <=16else((n-17)//8+8,n-17,3)if n<=32else\
             ((n-33)//16+10,n-33,4      )if n<=64else((n-65)//32+12,n-65,5)if\
             n<=128else((n-129)//64      +14,n-129,6)if n<=256else((n-257)//128\
             +16,n-257,7)if n<=512      else((n-513)//256+18,n-513,8)if n<=1024\
            else((n-1025)//512+20,n-      1025,9)if n<=2048else((n-2049)//1024+\
            22,n-2049 ,10)if n<=4096    else((n-4097)//2048+24,n-4097,11)if n\
            <=8192else((n-8193)//4096   +26,n-8193,12)if n<=16384else((n-16385\
            )//8192+28,n-16385,13)      if n<=32768else None;W=lambda compressed\
            :[(B:='110'),[[[(inter4      :=T(F.indicator)),(E:=inter4[0]),(H:=\
            inter4[1] )],(B:=(B+f'{E:0{H}b}'f''))][-1]if F.length<=1else[[(inter5\
            :=U(F.length)),(E:=inter5   [0]),(G:=inter5[1]),(C:=inter5[2])],(\
            B:=(B+f'{E:07b}'[-7:])      ),(B:=(B+f'{G:0{C}b}'[-C:][::-1]))if C\
            >=1else None,[(inter6:=    V(F.offset)),(E:=inter6[0]),(G:=inter6\
            [1]),(C:=inter6[2])],(     B:=(B+f'{E:05b}'[-5:])),(B:=(B+f'{G:0{C}b}'\
            f''[-C:][::-1]))if C>=    1else None][-1]for F in compressed],b''\
            .join([D(B[A:A+8][::-1    ],2).to_bytes(1,byteorder='big',signed=\
            False)for A in J(0,A(B    ),8)])+b'\x00'][-1];X=lambda filename,strk\
            :[(D:=strk),(S:=R(D)),(J:=W(S)),(G:=filename.encode(C)),(K:=A(G))\
            ,(B:=time.localtime()),(L:=(B.tm_year-1980<<9|B.tm_mon<<5|B.tm_mday\
            )),(M:=(B.tm_hour<<11|B.tm_min<<5|B.tm_sec//2)),(N:=Q.crc32(D.encode\
            (C))),(O:=A(D.encode(C))),(H:=A(J)),(P:=(b'PK\x03\x04'+E.pack('<2'\
            'B4HL2L2H',20,20,0,8,L,M,N,H,O,K,0)+G)),(I:=(b'PK\x01\x02'+E.pack\
            ('<4B4HL2L5H2L',20,20,20,20,0,8,L,M,N,H,O,K,0,0,0,0,32,0))),(I:=(\
            I+G)),(T:=E.pack('<4s4H2LH',b'PK\x05\x06',0,0,1,1,A(I),A(P)+H,0))\
            ,(U:=(P+J+I+T)),((V:=getattr(open(F,'wb'),'__enter__')()),V.write\
           (U),getattr(open(F,'wb'),'__exit__')())[1]][-1];H='"Did you win yo'\
           'ur sword fight?"\n            "Of course I won the fucking sword '\
           'fight," Hiro says. "I\'m the greatest sword fighter in the world.'\
           '"\n            "And you wrote the software."\n            "Yeah. '\
           'That, too," Hiro says.",\n        ';X(G,H);Y=open(F,'rb');I=M.ZipFile\
           (Y);assert I.namelist()==[G];assert I.read(G)==H.encode(C);N(F);##
```
Try running this ascii art in your Python environment of choice, and it will work identically to the non-transpiled version
in `test/test_scripts/zipy.py`.

### Limitations
The following are not supported because they do not have equivalent expression equivalents, and I wasn't able to figure out
some amalgamation of expressions that would emulate their behavior.

- Does not support error handling
- Does not support `async`
- Does not support statements like `yield`, `break`, `del`, `continue`
