from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sf_change_ledger.models import ConfigObject
from sf_change_ledger.normalise import normalise_value


PICKLIST_ID_KEYS = ("picklistId", "picklist_id", "Picklist ID", "id")
VALUE_ID_KEYS = ("externalCode", "external_code", "External Code", "optionId", "value")


def parse_picklist_file(path: Path) -> list[ConfigObject]:
    if path.suffix.lower() == ".json":
        return _parse_json(path)
    if path.suffix.lower() == ".csv":
        return _parse_csv(path)
    return []


def _parse_json(path: Path) -> list[ConfigObject]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "picklists" in data:
        data = data["picklists"]
    if isinstance(data, dict):
        data = [{"picklistId": key, "values": value} for key, value in data.items()]
    if not isinstance(data, list):
        raise ValueError(f"Unsupported picklist JSON shape in {path}")

    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        values = item.get("values") or item.get("options")
        picklist_id = _first_present(item, PICKLIST_ID_KEYS)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    row = dict(value)
                    row["picklistId"] = picklist_id
                    rows.append(row)
        else:
            rows.append(item)
    return _rows_to_objects(rows, path)


def _parse_csv(path: Path) -> list[ConfigObject]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return _rows_to_objects(rows, path)


def _rows_to_objects(rows: list[dict[str, Any]], path: Path) -> list[ConfigObject]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        picklist_id = _first_present(row, PICKLIST_ID_KEYS)
        value_id = _first_present(row, VALUE_ID_KEYS)
        if not picklist_id:
            continue
        picklist = grouped.setdefault(str(picklist_id), {"values": {}})
        if value_id:
            picklist["values"][str(value_id)] = normalise_value(row)
        else:
            picklist.update(normalise_value(row))

    objects: list[ConfigObject] = []
    for picklist_id, props in sorted(grouped.items()):
        objects.append(
            ConfigObject(
                kind="picklist",
                object_id=f"picklist:{picklist_id}",
                label=picklist_id,
                properties={},
                source=str(path),
            )
        )
        for value_id, value_props in sorted(props.get("values", {}).items()):
            objects.append(
                ConfigObject(
                    kind="picklist_value",
                    object_id=f"picklist_value:{picklist_id}.{value_id}",
                    label=f"{picklist_id}.{value_id}",
                    properties=normalise_value(value_props),
                    source=str(path),
                )
            )
    return objects


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None
