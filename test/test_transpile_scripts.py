import pytest
import os

from exprify import transpiled_script

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
    print(transpiled_script(filename))
