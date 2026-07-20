from pathlib import Path

from sf_change_ledger.diff import compare_snapshots
from sf_change_ledger.ingest import load_snapshot
from sf_change_ledger.risk import assess_diff

ROOT = Path(__file__).parents[1]


def _sample_result():
    left = load_snapshot(ROOT / "samples" / "before", "before")
    right = load_snapshot(ROOT / "samples" / "after", "after")
    return assess_diff(compare_snapshots(left, right))


def test_compare_detects_semantic_changes() -> None:
    result = _sample_result()

    assert len(result.added) == 2
    assert len(result.removed) == 0
    assert len(result.modified) == 3


def test_required_field_change_is_critical() -> None:
    result = _sample_result()
    department = next(
        change
        for change in result.changes
        if change.object_id == "metadata_field:EmpJob.department"
    )

    assert department.severity == "CRITICAL"
    assert any(change.path == "nullable" for change in department.property_changes)


def test_picklist_status_change_is_high() -> None:
    result = _sample_result()
    value = next(
        change
        for change in result.changes
        if change.object_id == "picklist_value:eventReason.DATACHG"
    )

    assert value.severity == "HIGH"
    assert "picklist value status changed" in value.explanation.lower()
