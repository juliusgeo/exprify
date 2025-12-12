import pytest
from .utils import exec_with_output

from tokenize import TokenInfo, STRING
from exprify import reflow, partition_token

OUTLINES_PATH = "reflow_outlines"
SCRIPTS_PATH = "test_scripts"


@pytest.mark.parametrize(
    ("script", "outline"),
    [
        ("test_scripts/zipy.py", "reflow_outlines/outline1.txt"),
        ("test_scripts/rijndael.py", "reflow_outlines/outline2.txt"),
    ],
)
def test_reflow_script(script, outline):
    outline = open(outline).read()
    script = open(script).read()
    for tolerance in range(0, 10):
        reflowed_script = reflow(script, outline, tolerance=tolerance)
        assert exec_with_output(reflowed_script) == exec_with_output(script)


def test_reflow_snippet():
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
    reflowed_script = reflow(script, outline, tolerance=4)
    print(reflowed_script)
    assert exec_with_output(reflowed_script) == exec_with_output(script)


def test_reflow_f_string():
    script = """
f'{10:0{10}b}'
f'{10:0b}'
    """
    outline = """
    8888888
    88888888
    888888888888
    """
    reflowed_script = reflow(script, outline, tolerance=0)
    print(reflowed_script)
    assert exec_with_output(reflowed_script) == exec_with_output(script)


def test_reflow_escape():
    script = """
b'\\x05'
b'\\x04bb'
    """
    outline = """
    88888
    88888
    88888
    88888
    """
    reflowed_script = reflow(script, outline, tolerance=0)
    print(reflowed_script)
    assert exec_with_output(reflowed_script) == exec_with_output(script)


def test_partition_escape():
    token = TokenInfo(string="f'\x05\x04'", type=STRING, start=0, end=0, line=0)
    assert partition_token(token, 3, 0)[0].string == "f'\x05'"
    assert partition_token(token, 4, 0)[0].string == "f'\x05\x04'"
