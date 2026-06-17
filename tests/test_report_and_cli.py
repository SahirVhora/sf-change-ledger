from pathlib import Path

from sf_change_ledger.cli import main


ROOT = Path(__file__).parents[1]


def test_cli_writes_markdown_change_pack(tmp_path: Path) -> None:
    out = tmp_path / "change-pack.md"

    exit_code = main(
        [
            "compare",
            "--left",
            str(ROOT / "samples" / "before"),
            "--right",
            str(ROOT / "samples" / "after"),
            "--left-label",
            "Pre Release",
            "--right-label",
            "Post Release",
            "--out",
            str(out),
        ]
    )

    assert exit_code == 0
    report = out.read_text(encoding="utf-8")
    assert "# SF Change Ledger Report" in report
    assert "## Testing Checklist" in report
    assert "CRITICAL: EmpJob.department" in report
    assert "Release Notes" not in report


def test_cli_writes_html_report(tmp_path: Path) -> None:
    out = tmp_path / "change-pack.html"

    exit_code = main(
        [
            "compare",
            "--left",
            str(ROOT / "samples" / "before"),
            "--right",
            str(ROOT / "samples" / "after"),
            "--out",
            str(out),
        ]
    )

    assert exit_code == 0
    assert "<!doctype html>" in out.read_text(encoding="utf-8").lower()
