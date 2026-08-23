import json
from pathlib import Path

from sf_change_ledger.assurance import build_change_assurance
from sf_change_ledger.models import ChangeKind, DiffResult, ObjectChange
from sf_change_ledger.report import write_report

from sapsf_shared.assurance import validate_assurance_document


def _result(severity="CRITICAL"):
    return DiffResult(
        left_label="Before",
        right_label="After",
        changes=[
            ObjectChange(
                kind=ChangeKind.MODIFIED,
                object_type="metadata_field",
                object_id="EmpJob.company",
                label="Company",
                severity=severity,
                explanation="Required flag changed.",
                test_focus=["Retest Job Information imports."],
            )
        ],
    )


def test_critical_change_blocks_and_validates():
    document = build_change_assurance(
        _result(), b"synthetic report", run_id="RUN-1", evidence_type="change_report_json"
    )
    validate_assurance_document(document)
    assert document["summary"]["status"] == "blocked"
    assert document["findings"][0]["severity"] == "critical"
    assert "before" not in document["findings"][0]
    assert "after" not in document["findings"][0]


def test_clean_diff_passes():
    document = build_change_assurance(
        DiffResult("Before", "After", []), b"{}", run_id="RUN-2", evidence_type="json"
    )
    assert document["summary"]["status"] == "pass"
    assert document["findings"] == []


def test_every_report_gets_restricted_assurance_sidecar(tmp_path: Path):
    report = tmp_path / "change-pack.json"
    write_report(_result("HIGH"), report)
    sidecar = tmp_path / "change-pack_assurance.json"
    assert report.exists()
    assert sidecar.stat().st_mode & 0o777 == 0o600
    validate_assurance_document(json.loads(sidecar.read_text(encoding="utf-8")))
