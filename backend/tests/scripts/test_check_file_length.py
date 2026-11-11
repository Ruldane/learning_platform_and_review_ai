from pathlib import Path

from scripts.check_file_length import check_paths, main


def test_file_of_300_lines_passes(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("x = 1\n" * 300)
    assert check_paths([f]) == []


def test_file_of_301_lines_is_flagged(tmp_path: Path) -> None:
    f = tmp_path / "big.py"
    f.write_text("x = 1\n" * 301)
    [v] = check_paths([f])
    assert (v.kind, v.count) == ("file", 301)


def test_function_of_51_lines_is_flagged(tmp_path: Path) -> None:
    body = "".join("    a = 1\n" for _ in range(50))
    f = tmp_path / "fn.py"
    f.write_text(f"def long():\n{body}")
    [v] = check_paths([f])
    assert (v.kind, v.name, v.count) == ("function", "long", 51)


def test_async_and_nested_functions_are_measured_separately(tmp_path: Path) -> None:
    inner = "".join("        b = 2\n" for _ in range(10))
    f = tmp_path / "n.py"
    f.write_text(f"async def outer():\n    def inner():\n{inner}    return inner\n")
    assert check_paths([f]) == []


def test_cli_exits_1_on_violation(tmp_path: Path) -> None:
    f = tmp_path / "big.py"
    f.write_text("x = 1\n" * 301)
    assert main([str(f)]) == 1
