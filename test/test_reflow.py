import pytest
import os

from exprify import reflow

OUTLINES_PATH = "reflow_outlines"
SCRIPTS_PATH = "test_scripts"


@pytest.mark.parametrize(
    ("outline"),
    [
        os.path.join(OUTLINES_PATH, i)
        for i in os.listdir(OUTLINES_PATH)
        if i.endswith(".txt")
    ],
)
def test_reflow(outline):
    reflowed_script = reflow("test_scripts/zipy.py", outline)
    print(reflowed_script)
    namespace = {}
    exec(reflowed_script, namespace)
