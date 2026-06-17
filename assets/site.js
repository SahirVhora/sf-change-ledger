const state = {
  result: null,
  activeSeverity: "all",
};

const noiseKeys = new Set([
  "__metadata",
  "lastModifiedDateTime",
  "lastModifiedOn",
  "createdDateTime",
  "createdOn",
  "mdfSystemCreatedDate",
  "mdfSystemLastModifiedDate",
]);

const severityRank = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeValue(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeValue).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([key, item]) => !noiseKeys.has(key) && item !== "" && item !== null)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, item]) => [key, normalizeValue(item)])
    );
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.toLowerCase() === "true") return true;
    if (trimmed.toLowerCase() === "false") return false;
    if (["none", "null"].includes(trimmed.toLowerCase())) return null;
    return trimmed;
  }
  return value;
}

function flatten(value, prefix = "", output = {}) {
  Object.entries(value || {}).forEach(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (item && typeof item === "object" && !Array.isArray(item)) flatten(item, path, output);
    else output[path] = item;
  });
  return output;
}

function attr(element, name) {
  const match = Array.from(element.attributes).find(
    (item) => item.localName.toLowerCase() === name.toLowerCase()
  );
  return match ? match.value : null;
}

function parseMetadata(text, source) {
  const documentNode = new DOMParser().parseFromString(text, "application/xml");
  const parseError = documentNode.querySelector("parsererror");
  if (parseError) throw new Error(`${source}: invalid XML`);

  const objects = [];
  Array.from(documentNode.getElementsByTagNameNS("*", "EntityType")).forEach((entity) => {
    const entityName = attr(entity, "Name");
    if (!entityName) return;
    objects.push({
      kind: "metadata_entity",
      objectId: `metadata_entity:${entityName}`,
      label: entityName,
      properties: {},
      source,
    });
    Array.from(entity.children)
      .filter((child) => child.localName === "Property")
      .forEach((property) => {
        const propertyName = attr(property, "Name");
        if (!propertyName) return;
        const properties = normalizeValue({
          type: attr(property, "Type"),
          nullable: attr(property, "Nullable") || "true",
          max_length: attr(property, "MaxLength"),
          label: attr(property, "label"),
          creatable: attr(property, "creatable"),
          updatable: attr(property, "updatable"),
          visible: attr(property, "visible"),
          required: attr(property, "required"),
          picklist: attr(property, "filter-restriction"),
        });
        objects.push({
          kind: "metadata_field",
          objectId: `metadata_field:${entityName}.${propertyName}`,
          label: `${entityName}.${propertyName}`,
          properties,
          source,
        });
      });
  });
  return objects;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"' && quoted && text[index + 1] === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(cell);
      if (row.some((item) => item !== "")) rows.push(row);
      row = [];
      cell = "";
    } else cell += char;
  }
  row.push(cell);
  if (row.some((item) => item !== "")) rows.push(row);
  if (!rows.length) return [];
  const headers = rows[0].map((item) => item.trim());
  return rows.slice(1).map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]))
  );
}

function firstPresent(row, keys) {
  const key = keys.find((candidate) => row[candidate] !== undefined && row[candidate] !== "");
  return key ? row[key] : null;
}

function picklistRowsToObjects(rows, source) {
  const groups = new Map();
  rows.forEach((row) => {
    const picklistId = firstPresent(row, ["picklistId", "picklist_id", "Picklist ID", "id"]);
    const valueId = firstPresent(row, ["externalCode", "external_code", "External Code", "optionId", "value"]);
    if (!picklistId) return;
    if (!groups.has(String(picklistId))) groups.set(String(picklistId), new Map());
    if (valueId) groups.get(String(picklistId)).set(String(valueId), normalizeValue(row));
  });

  const objects = [];
  Array.from(groups.entries()).sort().forEach(([picklistId, values]) => {
    objects.push({
      kind: "picklist",
      objectId: `picklist:${picklistId}`,
      label: picklistId,
      properties: {},
      source,
    });
    Array.from(values.entries()).sort().forEach(([valueId, properties]) => {
      objects.push({
        kind: "picklist_value",
        objectId: `picklist_value:${picklistId}.${valueId}`,
        label: `${picklistId}.${valueId}`,
        properties,
        source,
      });
    });
  });
  return objects;
}

function parsePicklistJson(text, source) {
  let data = JSON.parse(text);
  if (data && !Array.isArray(data) && data.picklists) data = data.picklists;
  if (data && !Array.isArray(data)) {
    data = Object.entries(data).map(([picklistId, values]) => ({ picklistId, values }));
  }
  if (!Array.isArray(data)) throw new Error(`${source}: unsupported picklist JSON shape`);
  const rows = [];
  data.forEach((item) => {
    if (!item || typeof item !== "object") return;
    const picklistId = firstPresent(item, ["picklistId", "picklist_id", "Picklist ID", "id"]);
    const values = item.values || item.options;
    if (Array.isArray(values)) {
      values.forEach((value) => {
        if (value && typeof value === "object") rows.push({ ...value, picklistId });
      });
    } else rows.push(item);
  });
  return picklistRowsToObjects(rows, source);
}

async function loadSnapshot(files, label) {
  const objects = new Map();
  for (const file of files) {
    const text = await file.text();
    const extension = file.name.toLowerCase().split(".").pop();
    let parsed = [];
    if (extension === "xml") parsed = parseMetadata(text, file.name);
    else if (extension === "json") parsed = parsePicklistJson(text, file.name);
    else if (extension === "csv") parsed = picklistRowsToObjects(parseCsv(text), file.name);
    parsed.forEach((item) => objects.set(item.objectId, item));
  }
  return { label, objects };
}

function propertyChanges(before, after) {
  const left = flatten(before);
  const right = flatten(after);
  return Array.from(new Set([...Object.keys(left), ...Object.keys(right)]))
    .sort()
    .filter((path) => JSON.stringify(left[path]) !== JSON.stringify(right[path]))
    .map((path) => ({ path, before: left[path], after: right[path] }));
}

function assess(change) {
  if (change.changeKind === "REMOVED") {
    if (["metadata_field", "picklist_value"].includes(change.objectType)) {
      return ["HIGH", "A field or picklist value was removed. Imports, rules, workflows, or integrations may still reference it.", "Run regression tests for transactions and integrations using this object."];
    }
    return ["MEDIUM", "A configuration object was removed. Confirm it is unused before transport or deployment.", "Check downstream references and confirm the removal is approved."];
  }
  if (change.changeKind === "ADDED") {
    if (change.objectType === "metadata_field") {
      return ["LOW", "A new metadata field was added. It is usually low risk unless made required or used by integrations.", "Check whether integrations or templates need the new field."];
    }
    return ["LOW", "A new configuration object was added.", "Confirm ownership and intended module scope."];
  }

  const changedTo = (suffix, target) =>
    change.propertyChanges.some((item) => item.path.endsWith(suffix) && String(item.after).toLowerCase() === target);
  if (changedTo("nullable", "false") || changedTo("required", "true")) {
    return ["CRITICAL", "A field appears to have become mandatory. This can block hire, job change, import, or integration flows if the value is missing.", "Test create/update flows and inbound integrations for this entity."];
  }
  if (change.objectType === "picklist_value" && change.propertyChanges.some((item) => item.path.endsWith("status"))) {
    return ["HIGH", "A picklist value status changed. Existing data, imports, and business rules may still depend on the old value.", "Test transactions and rules that select or validate this picklist value."];
  }
  if (change.propertyChanges.some((item) => item.path.endsWith("type") || item.path.endsWith("max_length"))) {
    return ["HIGH", "A field type or length changed. This can break integrations, templates, or validation logic.", "Test inbound files, API payloads, and reports using this field."];
  }
  if (["metadata_field", "picklist", "picklist_value"].includes(change.objectType)) {
    return ["MEDIUM", "A SuccessFactors configuration property changed and should be included in regression scope.", "Review field usage, picklist dependencies, and affected templates."];
  }
  return ["LOW", "A low-risk configuration property changed.", "Review during normal configuration validation."];
}

function compareSnapshots(left, right) {
  const ids = Array.from(new Set([...left.objects.keys(), ...right.objects.keys()])).sort();
  const changes = [];
  ids.forEach((objectId) => {
    const before = left.objects.get(objectId);
    const after = right.objects.get(objectId);
    let change = null;
    if (!before && after) {
      change = { changeKind: "ADDED", objectType: after.kind, objectId, label: after.label, propertyChanges: [] };
    } else if (before && !after) {
      change = { changeKind: "REMOVED", objectType: before.kind, objectId, label: before.label, propertyChanges: [] };
    } else if (before && after) {
      const differences = propertyChanges(before.properties, after.properties);
      if (differences.length) {
        change = { changeKind: "MODIFIED", objectType: after.kind, objectId, label: after.label, propertyChanges: differences };
      }
    }
    if (change) {
      const [severity, explanation, testFocus] = assess(change);
      changes.push({ ...change, severity, explanation, testFocus });
    }
  });
  changes.sort((a, b) => severityRank[b.severity] - severityRank[a.severity] || a.objectId.localeCompare(b.objectId));
  return { leftLabel: left.label, rightLabel: right.label, changes };
}

function counts(result) {
  const output = { total: result.changes.length, added: 0, removed: 0, modified: 0, critical: 0, high: 0, medium: 0, low: 0 };
  result.changes.forEach((change) => {
    output[change.changeKind.toLowerCase()] += 1;
    output[change.severity.toLowerCase()] += 1;
  });
  return output;
}

function displayValue(value) {
  if (value === undefined || value === null) return "(not set)";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function renderResults(beforeFiles, afterFiles) {
  const result = state.result;
  const summary = counts(result);
  document.getElementById("comparison_title").textContent = `${result.leftLabel} → ${result.rightLabel}`;
  document.getElementById("comparison_files").textContent = `${beforeFiles.length} before file(s), ${afterFiles.length} after file(s)`;
  document.getElementById("metrics_strip").innerHTML = [
    ["total", "Total changes", ""],
    ["critical", "Critical", "critical-metric"],
    ["high", "High", "high-metric"],
    ["modified", "Modified", ""],
    ["added", "Added", ""],
    ["removed", "Removed", ""],
  ].map(([key, label, className]) => `<div class="${className}"><strong>${summary[key]}</strong><span>${label}</span></div>`).join("");

  document.getElementById("changes_body").innerHTML = result.changes.map((change) => {
    const details = change.propertyChanges.length
      ? `<details><summary>${change.propertyChanges.length} field change(s)</summary><div class="property-list">${
          change.propertyChanges.map((item) => `<div><code>${escapeHtml(item.path)}</code><span>${escapeHtml(displayValue(item.before))} → ${escapeHtml(displayValue(item.after))}</span></div>`).join("")
        }</div></details>`
      : '<span>Object-level change</span>';
    const search = `${change.label} ${change.objectType} ${change.explanation} ${change.propertyChanges.map((item) => item.path).join(" ")}`;
    return `<tr class="change-row" data-severity="${change.severity.toLowerCase()}" data-search="${escapeHtml(search.toLowerCase())}">
      <td><span class="severity-badge ${change.severity.toLowerCase()}">${change.severity}</span></td>
      <td><strong>${change.changeKind}</strong><span>${escapeHtml(change.objectType)}</span></td>
      <td><strong>${escapeHtml(change.label)}</strong><code>${escapeHtml(change.objectId)}</code></td>
      <td>${escapeHtml(change.explanation)}</td>
      <td>${details}</td>
    </tr>`;
  }).join("");

  const tests = Array.from(new Set(result.changes.map((change) => change.testFocus))).sort();
  document.getElementById("testing_list").innerHTML = tests.length
    ? tests.map((test, index) => `<li><input type="checkbox" id="test_${index}"><label for="test_${index}">${escapeHtml(test)}</label></li>`).join("")
    : "<li>No regression activities were generated.</li>";
  document.getElementById("upload_workspace").hidden = true;
  document.getElementById("results_workspace").hidden = false;
  applyFilters();
}

function showError(message) {
  const banner = document.getElementById("error_banner");
  banner.textContent = message;
  banner.hidden = false;
}

function clearError() {
  document.getElementById("error_banner").hidden = true;
}

async function runComparison() {
  clearError();
  const beforeFiles = Array.from(document.getElementById("before_files").files);
  const afterFiles = Array.from(document.getElementById("after_files").files);
  if (!beforeFiles.length || !afterFiles.length) {
    showError("Choose at least one Before file and one After file.");
    return;
  }
  const button = document.getElementById("compare_button");
  button.disabled = true;
  button.textContent = "Comparing…";
  try {
    const before = await loadSnapshot(beforeFiles, document.getElementById("before_label").value.trim() || "Before");
    const after = await loadSnapshot(afterFiles, document.getElementById("after_label").value.trim() || "After");
    if (!before.objects.size || !after.objects.size) throw new Error("No supported SuccessFactors objects were found in one of the snapshots.");
    state.result = compareSnapshots(before, after);
    renderResults(beforeFiles, afterFiles);
  } catch (error) {
    showError(error.message || "The files could not be compared.");
  } finally {
    button.disabled = false;
    button.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 3v18h18M7 16l4-4 3 3 5-7"/></svg>Generate comparison';
  }
}

function applyFilters() {
  const query = document.getElementById("change_search").value.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll(".change-row").forEach((row) => {
    const matchesSeverity = state.activeSeverity === "all" || row.dataset.severity === state.activeSeverity;
    const matchesSearch = !query || row.dataset.search.includes(query);
    row.hidden = !(matchesSeverity && matchesSearch);
    if (!row.hidden) visible += 1;
  });
  document.getElementById("empty_filter").hidden = visible !== 0;
}

function markdownReport() {
  const result = state.result;
  const summary = counts(result);
  const tests = Array.from(new Set(result.changes.map((change) => change.testFocus))).sort();
  const lines = [
    "# SF Change Ledger Report", "",
    `Compared \`${result.leftLabel}\` to \`${result.rightLabel}\`.`, "",
    "## Summary", "",
    `- Total changes: ${summary.total}`,
    `- Added: ${summary.added}`,
    `- Removed: ${summary.removed}`,
    `- Modified: ${summary.modified}`,
    `- Critical: ${summary.critical}`,
    `- High: ${summary.high}`,
    `- Medium: ${summary.medium}`,
    `- Low: ${summary.low}`, "",
    "## Testing Checklist", "",
    ...tests.map((test) => `- [ ] ${test}`), "",
    "## Detailed Changes", "",
  ];
  result.changes.forEach((change) => {
    lines.push(`### ${change.severity}: ${change.label}`, "", `- Type: \`${change.objectType}\``, `- Change: \`${change.changeKind}\``, `- ID: \`${change.objectId}\``, `- Why it matters: ${change.explanation}`, "");
    if (change.propertyChanges.length) {
      lines.push("| Property | Before | After |", "|---|---|---|");
      change.propertyChanges.forEach((item) => lines.push(`| \`${item.path}\` | \`${displayValue(item.before)}\` | \`${displayValue(item.after)}\` |`));
      lines.push("");
    }
  });
  return `${lines.join("\n")}\n`;
}

function htmlReport() {
  const result = state.result;
  const summary = counts(result);
  const changes = result.changes.map((change) => `<section><h2>${escapeHtml(change.severity)}: ${escapeHtml(change.label)}</h2><p><strong>${escapeHtml(change.changeKind)} · ${escapeHtml(change.objectType)}</strong></p><p>${escapeHtml(change.explanation)}</p>${
    change.propertyChanges.length ? `<table><thead><tr><th>Property</th><th>Before</th><th>After</th></tr></thead><tbody>${change.propertyChanges.map((item) => `<tr><td>${escapeHtml(item.path)}</td><td>${escapeHtml(displayValue(item.before))}</td><td>${escapeHtml(displayValue(item.after))}</td></tr>`).join("")}</tbody></table>` : ""
  }</section>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><title>SF Change Ledger Report</title><style>body{font-family:Arial,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#17324d}header{border-bottom:3px solid #0f766e;padding-bottom:18px}section{border:1px solid #d5e0e4;padding:18px;margin-top:14px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #d5e0e4;padding:8px;text-align:left}.summary{display:flex;gap:24px;color:#60717c}</style></head><body><header><h1>SF Change Ledger</h1><p>${escapeHtml(result.leftLabel)} compared with ${escapeHtml(result.rightLabel)}</p><div class="summary"><span>${summary.total} changes</span><span>${summary.critical} critical</span><span>${summary.high} high</span></div></header>${changes}</body></html>`;
}

function excelRows() {
  const result = state.result;
  const summary = counts(result);
  const tests = Array.from(new Set(result.changes.map((change) => change.testFocus))).sort();
  return {
    Summary: [
      ["SF Change Ledger", "Configuration change report"],
      ["Baseline", result.leftLabel],
      ["Comparison", result.rightLabel],
      [],
      ["Metric", "Count"],
      ["Total changes", summary.total], ["Added", summary.added], ["Removed", summary.removed],
      ["Modified", summary.modified], ["Critical", summary.critical], ["High", summary.high],
      ["Medium", summary.medium], ["Low", summary.low],
    ],
    Changes: [
      ["Severity", "Change", "Object Type", "Object", "Object ID", "Why It Matters", "Test Focus"],
      ...result.changes.map((change) => [change.severity, change.changeKind, change.objectType, change.label, change.objectId, change.explanation, change.testFocus]),
    ],
    "Property Diffs": [
      ["Severity", "Object", "Property", "Before", "After"],
      ...result.changes.flatMap((change) => change.propertyChanges.map((item) => [change.severity, change.label, item.path, displayValue(item.before), displayValue(item.after)])),
    ],
    "Test Checklist": [["Status", "Test Activity"], ...tests.map((test) => ["Not started", test])],
  };
}

function downloadBlob(content, type, filename) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function downloadReport(format) {
  if (!state.result) return;
  if (format === "xlsx") {
    if (!window.XLSX) {
      showError("Excel support could not load. Check your internet connection, or use HTML/Markdown.");
      return;
    }
    const workbook = XLSX.utils.book_new();
    Object.entries(excelRows()).forEach(([name, rows]) => {
      const sheet = XLSX.utils.aoa_to_sheet(rows);
      sheet["!cols"] = rows[0].map((_, index) => ({ wch: index > 4 ? 55 : 24 }));
      XLSX.utils.book_append_sheet(workbook, sheet, name);
    });
    XLSX.writeFile(workbook, "sf-change-ledger-report.xlsx");
  } else if (format === "html") downloadBlob(htmlReport(), "text/html", "sf-change-ledger-report.html");
  else if (format === "md") downloadBlob(markdownReport(), "text/markdown", "sf-change-ledger-report.md");
  else downloadBlob(JSON.stringify(state.result, null, 2), "application/json", "sf-change-ledger-report.json");
}

function bindFileList(inputId, outputId) {
  document.getElementById(inputId).addEventListener("change", (event) => {
    const names = Array.from(event.target.files).map((file) => file.name);
    document.getElementById(outputId).textContent = names.length ? names.join(", ") : "No files selected";
  });
}

bindFileList("before_files", "before_file_list");
bindFileList("after_files", "after_file_list");
document.getElementById("compare_button").addEventListener("click", runComparison);
document.getElementById("new_comparison").addEventListener("click", () => {
  document.getElementById("results_workspace").hidden = true;
  document.getElementById("upload_workspace").hidden = false;
  clearError();
});
document.getElementById("change_search").addEventListener("input", applyFilters);
document.querySelectorAll(".filter-button").forEach((button) => {
  button.addEventListener("click", () => {
    state.activeSeverity = button.dataset.severity;
    document.querySelectorAll(".filter-button").forEach((item) => item.classList.toggle("active", item === button));
    applyFilters();
  });
});
document.querySelectorAll("[data-download]").forEach((button) => {
  button.addEventListener("click", () => downloadReport(button.dataset.download));
});
