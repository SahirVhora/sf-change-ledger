from __future__ import annotations

from sf_change_ledger.models import ChangeKind, DiffResult, ObjectChange, PropertyChange, Snapshot
from sf_change_ledger.normalise import flatten_properties


def compare_snapshots(left: Snapshot, right: Snapshot) -> DiffResult:
    changes: list[ObjectChange] = []
    all_ids = sorted(set(left.objects) | set(right.objects))

    for object_id in all_ids:
        before = left.objects.get(object_id)
        after = right.objects.get(object_id)
        if before is None and after is not None:
            changes.append(
                ObjectChange(
                    kind=ChangeKind.ADDED,
                    object_type=after.kind,
                    object_id=object_id,
                    label=after.label,
                    after=after,
                )
            )
            continue
        if before is not None and after is None:
            changes.append(
                ObjectChange(
                    kind=ChangeKind.REMOVED,
                    object_type=before.kind,
                    object_id=object_id,
                    label=before.label,
                    before=before,
                )
            )
            continue
        if before is None or after is None:
            continue

        property_changes = _compare_properties(before.properties, after.properties)
        if property_changes:
            changes.append(
                ObjectChange(
                    kind=ChangeKind.MODIFIED,
                    object_type=after.kind,
                    object_id=object_id,
                    label=after.label,
                    before=before,
                    after=after,
                    property_changes=property_changes,
                )
            )

    return DiffResult(left_label=left.label, right_label=right.label, changes=changes)


def _compare_properties(left: dict[str, object], right: dict[str, object]) -> list[PropertyChange]:
    left_flat = flatten_properties(left)
    right_flat = flatten_properties(right)
    changes: list[PropertyChange] = []
    for path in sorted(set(left_flat) | set(right_flat)):
        before = left_flat.get(path)
        after = right_flat.get(path)
        if before != after:
            changes.append(PropertyChange(path=path, before=before, after=after))
    return changes
