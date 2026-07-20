from __future__ import annotations

import secrets
import tempfile
from io import BytesIO
from pathlib import Path

from flask import Flask, abort, render_template, request, send_file
from sf_change_ledger.diff import compare_snapshots
from sf_change_ledger.ingest import load_snapshot
from sf_change_ledger.report import render_excel, render_html, render_json, render_markdown
from sf_change_ledger.risk import assess_diff
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {".xml", ".json", ".csv"}
REPORTS: dict[str, object] = {}
MAX_CACHED_REPORTS = 20


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,
        SECRET_KEY=secrets.token_hex(24),
    )

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/compare")
    def compare():
        before_files = request.files.getlist("before_files")
        after_files = request.files.getlist("after_files")
        before_label = request.form.get("before_label", "").strip() or "Before"
        after_label = request.form.get("after_label", "").strip() or "After"

        errors = _validate_uploads(before_files, after_files)
        if errors:
            return render_template("index.html", errors=errors), 400

        try:
            with tempfile.TemporaryDirectory(prefix="sf-change-ledger-") as temp:
                root = Path(temp)
                before_dir = root / "before"
                after_dir = root / "after"
                before_dir.mkdir()
                after_dir.mkdir()
                _save_uploads(before_files, before_dir)
                _save_uploads(after_files, after_dir)

                before = load_snapshot(before_dir, before_label)
                after = load_snapshot(after_dir, after_label)
                if not before.objects:
                    return render_template(
                        "index.html",
                        errors=["No supported SuccessFactors objects were found in Before files."],
                    ), 400
                if not after.objects:
                    return render_template(
                        "index.html",
                        errors=["No supported SuccessFactors objects were found in After files."],
                    ), 400

                result = assess_diff(compare_snapshots(before, after))
        except (ValueError, OSError) as exc:
            return render_template(
                "index.html", errors=[f"Could not process the uploads: {exc}"]
            ), 400

        report_id = secrets.token_urlsafe(12)
        REPORTS[report_id] = result
        while len(REPORTS) > MAX_CACHED_REPORTS:
            REPORTS.pop(next(iter(REPORTS)))

        return render_template(
            "results.html",
            result=result,
            report_id=report_id,
            before_files=[file.filename for file in before_files],
            after_files=[file.filename for file in after_files],
        )

    @app.get("/download/<report_id>/<format_name>")
    def download(report_id: str, format_name: str):
        result = REPORTS.get(report_id)
        if result is None:
            abort(404)

        renderers = {
            "xlsx": (
                render_excel,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "sf-change-ledger-report.xlsx",
                True,
            ),
            "html": (
                render_html,
                "text/html; charset=utf-8",
                "sf-change-ledger-report.html",
                False,
            ),
            "md": (
                render_markdown,
                "text/markdown; charset=utf-8",
                "sf-change-ledger-report.md",
                False,
            ),
            "json": (
                render_json,
                "application/json; charset=utf-8",
                "sf-change-ledger-report.json",
                False,
            ),
        }
        renderer_data = renderers.get(format_name)
        if renderer_data is None:
            abort(404)
        renderer, mimetype, filename, binary = renderer_data
        content = renderer(result)
        data = content if binary else content.encode("utf-8")
        return send_file(
            BytesIO(data),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename,
        )

    @app.errorhandler(413)
    def upload_too_large(_error):
        return render_template(
            "index.html",
            errors=["Upload is too large. The combined limit is 32 MB."],
        ), 413

    return app


def _validate_uploads(before_files: list[FileStorage], after_files: list[FileStorage]) -> list[str]:
    errors: list[str] = []
    if not any(file.filename for file in before_files):
        errors.append("Choose at least one Before file.")
    if not any(file.filename for file in after_files):
        errors.append("Choose at least one After file.")
    for group, files in (("Before", before_files), ("After", after_files)):
        for file in files:
            if not file.filename:
                continue
            if Path(file.filename).suffix.lower() not in ALLOWED_EXTENSIONS:
                errors.append(f"{group}: {file.filename} is not an XML, JSON, or CSV file.")
    return errors


def _save_uploads(files: list[FileStorage], target: Path) -> None:
    counters = {"xml": 0, "json": 0, "csv": 0}
    for upload in files:
        if not upload.filename:
            continue
        suffix = Path(upload.filename).suffix.lower()
        key = suffix.removeprefix(".")
        counters[key] += 1
        original = secure_filename(upload.filename)
        prefix = "metadata" if suffix == ".xml" else "picklist"
        upload.save(target / f"{prefix}_{counters[key]}_{original}")


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5075, debug=False)
