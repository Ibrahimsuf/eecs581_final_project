// --- Persistent stores in localStorage ---
const LS_SAVED = "savedJobs";       // array of job objects
const LS_HIDDEN = "hiddenJobIds";   // array of string ids

const $ = (sel) => document.querySelector(sel);
const resultsEl = $("#results");
const loadingEl = $("#loading");
const alertEl = $("#alert");
const savedCountEl = $("#savedCount");

let currentJobs = []; // last search results (array of jobs)

function readLS(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}
function writeLS(key, value) { localStorage.setItem(key, JSON.stringify(value)); }

function jobId(job) {
  // Prefer provided id; otherwise derive from title+company+url
  if (job.id) return String(job.id);
  const raw = `${job.title || ""}|${job.company || ""}|${job.url || ""}`;
  return btoa(unescape(encodeURIComponent(raw))).slice(0, 24); // short stable id
}

function getSaved() { return readLS(LS_SAVED, []); }
function getHidden() { return new Set(readLS(LS_HIDDEN, [])); }

function setSaved(arr) { writeLS(LS_SAVED, arr); updateSavedCount(); }
function setHidden(setObj) { writeLS(LS_HIDDEN, Array.from(setObj)); }

function updateSavedCount() {
  savedCountEl.textContent = getSaved().length;
}

// --- UI helpers ---
function showAlert(kind, msg) {
  alertEl.className = `alert alert-${kind}`;
  alertEl.textContent = msg;
  alertEl.classList.remove("d-none");
}
function hideAlert() { alertEl.classList.add("d-none"); }

function setLoading(on) {
  loadingEl.classList.toggle("d-none", !on);
}

function renderJobs(jobs) {
  const hidden = getHidden();
  const hideEnabled = $("#toggleHidden").checked;

  resultsEl.innerHTML = "";

  const visible = jobs.filter(j => hideEnabled ? !hidden.has(jobId(j)) : true);

  if (visible.length === 0) {
    resultsEl.innerHTML = `<div class="text-muted text-center py-5">No jobs to display.</div>`;
    return;
  }

  for (const job of visible) {
    const id = jobId(job);
    const saved = getSaved().some(j => jobId(j) === id);

    const card = document.createElement("div");
    card.className = "col-12 col-md-6 col-xl-4";
    card.innerHTML = `
      <div class="card h-100 shadow-sm">
        <div class="card-body d-flex flex-column">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h5 class="card-title me-2">${escapeHTML(job.title || "Untitled Role")}</h5>
            <button class="btn btn-sm ${saved ? "btn-success" : "btn-outline-success"} btn-save" data-id="${id}">
              <i class="bi ${saved ? "bi-bookmark-check" : "bi-bookmark"}"></i>
            </button>
          </div>
          <h6 class="card-subtitle mb-2 text-muted">${escapeHTML(job.company || "Unknown Company")}</h6>
          <div class="small mb-2"><i class="bi bi-geo-alt"></i> ${escapeHTML(job.location || "Remote/Unspecified")}</div>
          ${Array.isArray(job.skills) && job.skills.length ? `
            <div class="mb-3">${job.skills.slice(0,8).map(s => `<span class="badge text-bg-light me-1 mb-1">${escapeHTML(s)}</span>`).join("")}</div>
          ` : ""}
          <div class="mt-auto d-flex gap-2">
            ${job.url ? `<a class="btn btn-primary btn-sm flex-grow-1" href="${escapeAttr(job.url)}" target="_blank" rel="noopener">View</a>` : ""}
            <button class="btn btn-outline-secondary btn-sm flex-grow-1 btn-hide" data-id="${id}">
              <i class="bi bi-eye-slash"></i> Hide
            </button>
          </div>
        </div>
        ${job.posted_at ? `<div class="card-footer small text-muted">Posted: ${escapeHTML(job.posted_at)}</div>` : ""}
      </div>
    `;
    resultsEl.appendChild(card);
  }

  // Wire buttons after render
  resultsEl.querySelectorAll(".btn-hide").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const hidden = getHidden();
      hidden.add(id);
      setHidden(hidden);
      renderJobs(currentJobs);
    });
  });

  resultsEl.querySelectorAll(".btn-save").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const existing = getSaved();
      const found = existing.find(j => jobId(j) === id);
      if (found) {
        // remove from saved
        setSaved(existing.filter(j => jobId(j) !== id));
      } else {
        const job = currentJobs.find(j => jobId(j) === id);
        if (job) setSaved([job, ...existing]);
      }
      renderJobs(currentJobs);       // refresh icons
      renderSavedList();             // refresh drawer
    });
  });
}

function renderSavedList() {
  const container = $("#savedList");
  const saved = getSaved();

  container.innerHTML = saved.length
    ? ""
    : `<div class="text-muted">No saved jobs yet.</div>`;

  for (const job of saved) {
    const id = jobId(job);
    const div = document.createElement("div");
    div.className = "card shadow-sm";
    div.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <h6 class="mb-1">${escapeHTML(job.title || "Untitled Role")}</h6>
            <div class="small text-muted">${escapeHTML(job.company || "")} ${job.location ? "· " + escapeHTML(job.location) : ""}</div>
          </div>
          <div class="d-flex gap-2">
            ${job.url ? `<a class="btn btn-sm btn-primary" href="${escapeAttr(job.url)}" target="_blank" rel="noopener"><i class="bi bi-box-arrow-up-right"></i></a>` : ""}
            <button class="btn btn-sm btn-outline-danger btn-unsave" data-id="${id}">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
        </div>
      </div>
    `;
    container.appendChild(div);
  }

  container.querySelectorAll(".btn-unsave")?.forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      setSaved(getSaved().filter(j => jobId(j) !== id));
      renderSavedList();
      renderJobs(currentJobs);
    });
  });

  updateSavedCount();
}

// --- Networking / search ---
async function searchJobs(skills) {
  setLoading(true);
  hideAlert();
  try {
    // Default form-url-encoded POST to your Flask /get_jobs
    const res = await fetch("/get_jobs", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `skills=${encodeURIComponent(skills)}`
    });

    const data = await res.json();

    // Expecting: array of jobs. If your backend returns a different shape, adapt here.
    if (Array.isArray(data)) {
      currentJobs = data;
    } else if (Array.isArray(data.jobs)) {
      currentJobs = data.jobs;
    } else {
      currentJobs = [];
      showAlert("warning", "No job list returned from server.");
    }

    renderJobs(currentJobs);
  } catch (e) {
    showAlert("danger", "Network/server error while fetching jobs.");
    console.error(e);
  } finally {
    setLoading(false);
  }
}

// --- Event wiring ---
document.addEventListener("DOMContentLoaded", () => {
  updateSavedCount();

  // Form submit → search
  document.getElementById("skillForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const skills = document.getElementById("skills").value.trim();
    if (!skills) {
      showAlert("warning", "Please enter at least one skill.");
      return;
    }
    searchJobs(skills);
  });

  // Toggle hidden filter
  document.getElementById("toggleHidden").addEventListener("change", () => {
    renderJobs(currentJobs);
  });

  // Unhide all
  document.getElementById("btnClearHidden").addEventListener("click", () => {
    setHidden(new Set());
    renderJobs(currentJobs);
  });

  // Saved drawer controls
  const savedDrawer = new bootstrap.Offcanvas(document.getElementById("savedDrawer"));
  document.getElementById("btnShowSaved").addEventListener("click", () => {
    renderSavedList();
    savedDrawer.show();
  });
  document.getElementById("btnClearSaved").addEventListener("click", () => {
    setSaved([]);
    renderSavedList();
    renderJobs(currentJobs);
  });
});

// --- Simple escaping helpers ---
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
