from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeKind(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"


@dataclass(frozen=True)
class ConfigObject:
    kind: str
    object_id: str
    label: str
    properties: dict[str, Any]
    source: str


@dataclass(frozen=True)
class PropertyChange:
    path: str
    before: Any
    after: Any


@dataclass
class ObjectChange:
    kind: ChangeKind
    object_type: str
    object_id: str
    label: str
    before: ConfigObject | None = None
    after: ConfigObject | None = None
    property_changes: list[PropertyChange] = field(default_factory=list)
    severity: str = "LOW"
    explanation: str = ""
    test_focus: list[str] = field(default_factory=list)


@dataclass
class Snapshot:
    label: str
    objects: dict[str, ConfigObject]


@dataclass
class DiffResult:
    left_label: str
    right_label: str
    changes: list[ObjectChange]

    @property
    def added(self) -> list[ObjectChange]:
        return [change for change in self.changes if change.kind == ChangeKind.ADDED]

    @property
    def removed(self) -> list[ObjectChange]:
        return [change for change in self.changes if change.kind == ChangeKind.REMOVED]

    @property
    def modified(self) -> list[ObjectChange]:
        return [change for change in self.changes if change.kind == ChangeKind.MODIFIED]

    @property
    def by_severity(self) -> dict[str, int]:
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for change in self.changes:
            counts[change.severity] = counts.get(change.severity, 0) + 1
        return counts
