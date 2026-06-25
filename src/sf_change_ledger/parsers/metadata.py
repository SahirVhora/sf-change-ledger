from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from defusedxml.ElementTree import parse as _safe_parse

from sf_change_ledger.models import ConfigObject
from sf_change_ledger.normalise import normalise_value


def _name(element: ET.Element) -> str:
    return element.attrib.get("Name", "").strip()


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def _attribute(element: ET.Element, name: str) -> str | None:
    for key, value in element.attrib.items():
        if _local_name(key).lower() == name.lower():
            return value
    return None


def parse_metadata_file(path: Path) -> list[ConfigObject]:
    tree = _safe_parse(path)
    root = tree.getroot()
    objects: list[ConfigObject] = []

    for entity in (item for item in root.iter() if _local_name(item.tag) == "EntityType"):
        entity_name = _name(entity)
        if not entity_name:
            continue

        for prop in (item for item in entity if _local_name(item.tag) == "Property"):
            prop_name = _name(prop)
            if not prop_name:
                continue
            field_props = {
                "type": _attribute(prop, "Type"),
                "nullable": _attribute(prop, "Nullable") or "true",
                "max_length": _attribute(prop, "MaxLength"),
                "label": _attribute(prop, "label"),
                "creatable": _attribute(prop, "creatable"),
                "updatable": _attribute(prop, "updatable"),
                "visible": _attribute(prop, "visible"),
                "required": _attribute(prop, "required"),
                "picklist": _attribute(prop, "filter-restriction"),
            }
            objects.append(
                ConfigObject(
                    kind="metadata_field",
                    object_id=f"metadata_field:{entity_name}.{prop_name}",
                    label=f"{entity_name}.{prop_name}",
                    properties=normalise_value(field_props),
                    source=str(path),
                )
            )

        objects.append(
            ConfigObject(
                kind="metadata_entity",
                object_id=f"metadata_entity:{entity_name}",
                label=entity_name,
                properties={},
                source=str(path),
            )
        )

    return objects
