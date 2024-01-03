from io import StringIO
from contextlib import redirect_stdout


def exec_with_output(script):
    f = StringIO()
    with redirect_stdout(f):
        exec(script, {})
    return f.getvalue()
