import re
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_example_runs():
    blocks = re.findall(r"```python\n(.*?)```", README.read_text(), flags=re.DOTALL)
    assert blocks, "README.md contains no python example"
    exec(compile(blocks[0], "README example", "exec"), {})  # noqa: S102 -- runs the README example, which is trusted repository content


def test_readme_example_does_not_force_a_backend():
    blocks = re.findall(r"```python\n(.*?)```", README.read_text(), flags=re.DOTALL)
    assert "matplotlib.use" not in blocks[0]
