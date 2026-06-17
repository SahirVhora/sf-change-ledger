function renderFileList(inputId, outputId) {
  const input = document.getElementById(inputId);
  const output = document.getElementById(outputId);
  if (!input || !output) return;
  input.addEventListener("change", () => {
    const names = Array.from(input.files).map((file) => file.name);
    output.textContent = names.length ? names.join(", ") : "No files selected";
  });
}

renderFileList("before_files", "before_file_list");
renderFileList("after_files", "after_file_list");

const search = document.getElementById("change_search");
const rows = Array.from(document.querySelectorAll(".change-row"));
const buttons = Array.from(document.querySelectorAll(".filter-button"));
const empty = document.getElementById("empty_filter");
let activeSeverity = "all";

function applyFilters() {
  if (!rows.length) return;
  const query = (search?.value || "").trim().toLowerCase();
  let visible = 0;
  rows.forEach((row) => {
    const matchesSeverity =
      activeSeverity === "all" || row.dataset.severity === activeSeverity;
    const matchesSearch =
      !query || (row.dataset.search || "").toLowerCase().includes(query);
    row.hidden = !(matchesSeverity && matchesSearch);
    if (!row.hidden) visible += 1;
  });
  if (empty) empty.hidden = visible !== 0;
}

search?.addEventListener("input", applyFilters);
buttons.forEach((button) => {
  button.addEventListener("click", () => {
    activeSeverity = button.dataset.severity;
    buttons.forEach((item) => item.classList.toggle("active", item === button));
    applyFilters();
  });
});
