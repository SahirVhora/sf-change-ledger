from pathlib import Path

from sf_change_ledger.ingest import load_snapshot

ROOT = Path(__file__).parents[1]


def test_load_snapshot_parses_metadata_and_picklists() -> None:
    snapshot = load_snapshot(ROOT / "samples" / "before")

    assert "metadata_entity:EmpJob" in snapshot.objects
    assert "metadata_field:EmpJob.department" in snapshot.objects
    assert "picklist:eventReason" in snapshot.objects
    assert "picklist_value:eventReason.HIRNEW" in snapshot.objects
    assert len(snapshot.objects) == 10


def test_noise_properties_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "picklists.json"
    path.write_text(
        """
        {
          "picklists": [{
            "picklistId": "country",
            "values": [{
              "externalCode": "GBR",
              "status": "ACTIVE",
              "lastModifiedDateTime": "2026-01-01T00:00:00Z"
            }]
          }]
        }
        """,
        encoding="utf-8",
    )

    snapshot = load_snapshot(tmp_path)
    value = snapshot.objects["picklist_value:country.GBR"]
    assert "lastModifiedDateTime" not in value.properties
