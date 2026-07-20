from __future__ import annotations

from sf_change_ledger.models import ChangeKind, DiffResult, ObjectChange

SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def assess_diff(result: DiffResult) -> DiffResult:
    for change in result.changes:
        severity, explanation, tests = assess_change(change)
        change.severity = severity
        change.explanation = explanation
        change.test_focus = tests
    result.changes.sort(
        key=lambda item: (-SEVERITY_ORDER[item.severity], item.object_type, item.object_id)
    )
    return result


def assess_change(change: ObjectChange) -> tuple[str, str, list[str]]:
    if change.kind == ChangeKind.REMOVED:
        if change.object_type in {"metadata_field", "picklist_value"}:
            return (
                "HIGH",
                "A field or picklist value was removed. Imports, rules, workflows, or integrations may still reference it.",
                ["Run regression tests for transactions and integrations using this object."],
            )
        return (
            "MEDIUM",
            "A configuration object was removed. Confirm it is unused before transport or release.",
            ["Check downstream references and confirm the removal is approved."],
        )

    if change.kind == ChangeKind.ADDED:
        if change.object_type == "metadata_field":
            return (
                "LOW",
                "A new metadata field was added. It is usually low risk unless made required or used by integrations.",
                ["Check whether integrations or templates need the new field."],
            )
        return (
            "LOW",
            "A new configuration object was added.",
            ["Confirm ownership and intended module scope."],
        )

    paths = {item.path for item in change.property_changes}
    before_after = {
        (item.path, str(item.before), str(item.after)) for item in change.property_changes
    }

    if _path_changed_to(paths, before_after, "nullable", "false") or _path_changed_to(
        paths, before_after, "required", "true"
    ):
        return (
            "CRITICAL",
            "A field appears to have become mandatory. This can block hire, job change, import, or integration flows if the value is missing.",
            ["Test create/update flows and inbound integrations for this entity."],
        )

    if change.object_type == "picklist_value" and any(path.endswith("status") for path in paths):
        return (
            "HIGH",
            "A picklist value status changed. Existing data, imports, and business rules may still depend on the old value.",
            ["Test transactions and rules that select or validate this picklist value."],
        )

    if any(path.endswith("type") or path.endswith("max_length") for path in paths):
        return (
            "HIGH",
            "A field type or length changed. This can break integrations, templates, or validation logic.",
            ["Test inbound files, API payloads, and reports using this field."],
        )

    if change.object_type in {"metadata_field", "picklist", "picklist_value"}:
        return (
            "MEDIUM",
            "A SuccessFactors configuration property changed and should be included in regression scope.",
            ["Review field usage, picklist dependencies, and affected templates."],
        )

    return (
        "LOW",
        "A low-risk configuration property changed.",
        ["Review during normal release validation."],
    )


def _path_changed_to(
    paths: set[str], before_after: set[tuple[str, str, str]], suffix: str, target: str
) -> bool:
    if not any(path.endswith(suffix) for path in paths):
        return False
    return any(
        path.endswith(suffix) and after.lower() == target for path, _before, after in before_after
    )
