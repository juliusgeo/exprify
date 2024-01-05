from io import StringIO
from contextlib import redirect_stdout, redirect_stderr


def exec_with_output(script):
    f, g = StringIO(), StringIO()
    with redirect_stdout(f), redirect_stderr(g):
        exec(script, {})
    return f.getvalue() + g.getvalue()
