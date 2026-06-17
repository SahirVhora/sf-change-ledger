# Architecture

## Processing Pipeline

```text
snapshot folder
    |
    v
format parsers
    |
    v
normalised ConfigObject records
    |
    v
stable-ID semantic diff
    |
    v
risk and test-focus classification
    |
    v
Markdown / HTML / JSON change pack
```

## Design Principles

### Local first

The MVP reads exported configuration files and makes no tenant calls. This
keeps demos safe and allows consultants to use the tool in restricted client
environments.

### Semantic objects, not raw XML lines

Each parser emits the same `ConfigObject` model:

```text
kind
object_id
label
properties
source
```

The diff engine does not know whether an object came from XML, CSV, or JSON.
New export formats can therefore be added without changing risk or reporting.

### Stable IDs

Examples:

```text
metadata_entity:EmpJob
metadata_field:EmpJob.department
picklist:eventReason
picklist_value:eventReason.HIRNEW
```

Stable IDs are the basis for future history, timelines, and Git-style object
inspection.

## Current Modules

| Module | Responsibility |
|---|---|
| `ingest.py` | Discover supported files and assemble a snapshot |
| `parsers/metadata.py` | Convert OData EDMX metadata into entities and fields |
| `parsers/picklists.py` | Convert JSON/CSV picklist exports into stable objects |
| `normalise.py` | Remove timestamps/noise and canonicalise values |
| `diff.py` | Produce property-level semantic changes |
| `risk.py` | Assign severity, explanation, and regression focus |
| `report.py` | Render Markdown, HTML, and machine-readable JSON |
| `cli.py` | User-facing command interface |

## Planned Storage Layer

SQLite should be added when snapshot history becomes part of the product:

```text
snapshots
config_objects
object_versions
comparisons
findings
```

The current in-memory model is deliberately compatible with that structure.

## Parser Roadmap

1. MDF and corporate data model XML
2. Business rules
3. Workflow configuration
4. RBP role and permission exports
5. Event reasons and foundation-object associations

Each parser should produce stable IDs, strip export noise, and include focused
tests using anonymised fixtures.
