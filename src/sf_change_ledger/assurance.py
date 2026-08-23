from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sapsf_shared.assurance import new_assurance_document, validate_assurance_document
from sf_change_ledger import __version__
from sf_change_ledger.models import DiffResult

SEVERITY_MAP = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}


def build_change_assurance(
    result: DiffResult,
    evidence: bytes,
    *,
    run_id: str,
    evidence_type: str,
) -> dict[str, Any]:
    countries = [
        item.strip()
        for item in os.getenv("SAPSF_ENGAGEMENT_COUNTRIES", "").split(",")
        if item.strip()
    ]
    modules = [
        item.strip()
        for item in os.getenv("SAPSF_ENGAGEMENT_MODULES", "Employee Central").split(",")
        if item.strip()
    ]
    document = new_assurance_document(
        engagement_id=os.getenv("SAPSF_ENGAGEMENT_ID", "local-migration"),
        engagement_name=os.getenv("SAPSF_ENGAGEMENT_NAME", "Migration Assurance"),
        client_alias=os.getenv("SAPSF_CLIENT_ALIAS", "LOCAL-REVIEW"),
        run_id=run_id,
        tool="sf-change-ledger",
        tool_version=__version__,
    )
    document["engagement"].update(
        {
            "countries": countries,
            "modules": modules,
            "stage": os.getenv("SAPSF_ENGAGEMENT_STAGE", "cutover-readiness"),
        }
    )
    document["run"]["scope"] = {
        "baseline": result.left_label,
        "comparison": result.right_label,
        "change_count": len(result.changes),
    }
    evidence_id = "E-CHANGE-REPORT"
    document["evidence"] = [
        {
            "id": evidence_id,
            "type": evidence_type,
            "description": "Hashed local semantic configuration change report",
            "classification": "confidential",
            "source": "sf-change-ledger-report",
            "sha256": hashlib.sha256(evidence).hexdigest(),
            "generated_at": datetime.now(UTC).isoformat(),
        }
    ]
    counts: Counter[str] = Counter()
    for change in result.changes:
        severity = SEVERITY_MAP.get(str(change.severity).upper(), "low")
        counts[severity] += 1
        raw_id = "\x1f".join((change.kind.value, change.object_type, change.object_id))
        suffix = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16].upper()
        finding_id = f"F-{suffix}"
        action_id = f"A-{suffix}"
        document["findings"].append(
            {
                "id": finding_id,
                "rule_id": f"CHANGE-{change.kind.value}",
                "severity": severity,
                "status": "open",
                "category": "configuration_change",
                "title": f"{change.kind.value.title()} {change.object_type}",
                "description": change.explanation
                or "Configuration changed between the approved snapshots.",
                "object_type": change.object_type,
                "object_ref": change.object_id,
                "evidence_refs": [evidence_id],
                "action_refs": [action_id],
            }
        )
        test_focus = (
            "; ".join(change.test_focus)
            or "Review the change and confirm the required regression test."
        )
        document["actions"].append(
            {
                "id": action_id,
                "title": test_focus,
                "owner_role": "Configuration and Test Lead",
                "priority": severity
                if severity in {"critical", "high", "medium", "low"}
                else "low",
                "status": "open",
                "finding_refs": [finding_id],
            }
        )
    document["summary"] = {
        "status": "blocked"
        if counts["critical"]
        else ("attention_required" if result.changes else "pass"),
        "records_assessed": len(result.changes),
        "findings": len(document["findings"]),
        "by_severity": dict(sorted(counts.items())),
    }
    validate_assurance_document(document)
    return document


def render_assurance(result: DiffResult, evidence: bytes, run_id: str, evidence_type: str) -> str:
    document = build_change_assurance(
        result,
        evidence,
        run_id=run_id,
        evidence_type=evidence_type,
    )
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def write_assurance_sidecar(result: DiffResult, report_path: Path) -> Path:
    path = report_path.with_name(f"{report_path.stem}_assurance.json")
    content = report_path.read_bytes()
    rendered = render_assurance(
        result,
        content,
        run_id=report_path.stem,
        evidence_type=f"change_report_{report_path.suffix.lower().removeprefix('.') or 'text'}",
    )
    path.write_text(rendered, encoding="utf-8")
    path.chmod(0o600)
    return path
