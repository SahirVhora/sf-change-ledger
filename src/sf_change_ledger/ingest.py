from __future__ import annotations

from pathlib import Path

from sf_change_ledger.models import ConfigObject, Snapshot
from sf_change_ledger.parsers.metadata import parse_metadata_file
from sf_change_ledger.parsers.picklists import parse_picklist_file


def load_snapshot(path: str | Path, label: str | None = None) -> Snapshot:
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(root)
    if root.is_file():
        files = [root]
        snapshot_label = label or root.stem
    else:
        files = [file for file in root.rglob("*") if file.is_file()]
        snapshot_label = label or root.name

    objects: dict[str, ConfigObject] = {}
    for file in sorted(files):
        parsed = _parse_file(file)
        for obj in parsed:
            objects[obj.object_id] = obj

    return Snapshot(label=snapshot_label, objects=objects)


def _parse_file(path: Path) -> list[ConfigObject]:
    lower = path.name.lower()
    if lower.endswith(".xml") and ("metadata" in lower or lower == "$metadata.xml"):
        return parse_metadata_file(path)
    if lower.startswith("picklist") and path.suffix.lower() in {".json", ".csv"}:
        return parse_picklist_file(path)
    return []
