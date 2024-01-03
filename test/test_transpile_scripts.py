import pytest
import os

from exprify import transpiled_script
from .utils import exec_with_output

SCRIPTS_PATH = "test_scripts"


@pytest.mark.parametrize(
    "filename",
    [
        os.path.join(SCRIPTS_PATH, i)
        for i in os.listdir(SCRIPTS_PATH)
        if i.endswith(".py")
    ],
)
def test_transform_scripts(filename):
    assert exec_with_output(open(filename).read()) == exec_with_output(
        transpiled_script(filename)
    )
