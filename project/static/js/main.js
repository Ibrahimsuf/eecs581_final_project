// ===============================
// LocalStorage Keys
// ===============================
const LS_SAVED = "savedJobs";       // array of job objects
const LS_HIDDEN = "hiddenJobIds";   // array of string ids

const $ = (sel) => document.querySelector(sel);
const resultsEl = $("#results");
const loadingEl = $("#loading");
const alertEl = $("#alert");
const savedCountEl = $("#savedCount");

// Keeps last search results in memory
let currentJobs = [];

function readLS(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}

function writeLS(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

// ===============================
// Save & Hide Job Helpers
// ===============================
function isSaved(jobId) {
  return readLS(LS_SAVED, []).some(j => j.id === jobId);
}

function toggleSave(job) {
  let saved = readLS(LS_SAVED, []);

  if (isSaved(job.id)) {
    saved = saved.filter(j => j.id !== job.id);
  } else {
    saved.push(job);
  }

  writeLS(LS_SAVED, saved);
  updateSavedUI();
  renderJobs(currentJobs);
}

function updateSavedUI() {
  const saved = readLS(LS_SAVED, []);
  savedCountEl.textContent = saved.length;

  const list = $("#savedList");
  list.innerHTML = "";

  saved.forEach(job => {
    const item = document.createElement("div");
    item.className = "p-3 border rounded bg-white shadow-sm";

    item.innerHTML = `
      <div class="d-flex justify-content-between">
        <strong>${escapeHTML(job.title)}</strong>
        <button class="btn btn-sm btn-danger" onclick="toggleSave(${job.id})">
          <i class="bi bi-trash"></i>
        </button>
      </div>
      <div>${escapeHTML(job.company)}</div>
      <div class="text-muted">${escapeHTML(job.location)}</div>
    `;

    list.appendChild(item);
  });
}

// ===============================
// Hide Job Feature
// ===============================
function isHidden(jobId) {
  return readLS(LS_HIDDEN, []).includes(jobId);
}

function toggleHide(jobId) {
  let hidden = readLS(LS_HIDDEN, []);

  hidden = isHidden(jobId)
    ? hidden.filter(id => id !== jobId)
    : [...hidden, jobId];

  writeLS(LS_HIDDEN, hidden);
  renderJobs(currentJobs);
}

// ===============================
// Search Button Handler
// ===============================
$("#searchBtn").addEventListener("click", async () => {
  const hardSkills = $("#hardSkills").value
    .split(",")
    .map(s => s.trim().toLowerCase())
    .filter(Boolean);

  const softSkills = $("#softSkills").value
    .split(",")
    .map(s => s.trim().toLowerCase())
    .filter(Boolean);

  if (hardSkills.length === 0) {
    showAlert("Please enter at least one hard skill.");
    return;
  }

  const payload = {
    hardSkills: hardSkills,
    softSkills: softSkills
  };

  try {
    loadingEl.classList.remove("d-none");
    alertEl.classList.add("d-none");
    resultsEl.innerHTML = "";

    const resp = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      showAlert("Server error during search.");
      return;
    }

    const data = await resp.json();
    currentJobs = data.results;
    renderJobs(currentJobs);

  } catch (err) {
    showAlert("Network error: " + err.message);
  } finally {
    loadingEl.classList.add("d-none");
  }
});

// ===============================
// Render Job Results
// ===============================
function renderJobs(jobs) {
  resultsEl.innerHTML = "";

  const showHidden = $("#toggleHidden").checked;

  jobs.forEach(job => {
    const hidden = isHidden(job.id);
    if (hidden && !showHidden) return; // Skip hidden jobs unless shown

    const card = document.createElement("div");
    card.className = `job-card p-3 mb-3 border rounded bg-white shadow-sm ${hidden ? "opacity-50" : ""}`;

    card.innerHTML = `
      <div class="d-flex justify-content-between align-items-start">
        <h5>${escapeHTML(job.title)}</h5>
        <button class="btn btn-outline-primary btn-sm" onclick='toggleSave(${JSON.stringify(job)})'>
          ${isSaved(job.id) ? '<i class="bi bi-bookmark-fill"></i>' : '<i class="bi bi-bookmark"></i>'}
        </button>
      </div>

      <div><strong>${escapeHTML(job.company)}</strong></div>
      <div class="text-muted">${escapeHTML(job.location)}</div>

      <p class="mt-2">${escapeHTML(job.description)}</p>

      <div class="mt-2">
        <strong>Hard Skill Matches:</strong>
        ${job.hard_matches?.join(", ") || "None"}
      </div>

      <div class="mt-1">
        <strong>Soft Skill Matches:</strong>
        ${job.soft_matches?.join(", ") || "None"}
      </div>

      <div class="d-flex gap-2 mt-3">
        <button class="btn btn-warning btn-sm" onclick="toggleHide('${job.id}')">
          ${hidden ? "Unhide" : "Hide"}
        </button>
        <a href="${escapeAttr(job.url)}" target="_blank" class="btn btn-success btn-sm">
          Apply
        </a>
      </div>
    `;

    resultsEl.appendChild(card);
  });
}

// ===============================
// Alert Helper
// ===============================
function showAlert(msg) {
  alertEl.textContent = msg;
  alertEl.classList.remove("d-none");
}

// ===============================
// Escaping Utilities
// ===============================
function escapeHTML(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(s) {
  return escapeHTML(s).replaceAll("`", "&#96;");
}

// Initial load of saved list
updateSavedUI();
