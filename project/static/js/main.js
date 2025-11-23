// --- Persistent stores in localStorage ---
const LS_SAVED = "savedJobs";       // array of job objects
const LS_HIDDEN = "hiddenJobIds";   // array of string ids

const $ = (sel) => document.querySelector(sel);
const resultsEl = $("#results");
const loadingEl = $("#loading");
const alertEl = $("#alert");
const savedCountEl = $("#savedCount");

let currentJobs = []; // last search results (array of jobs)

// -----------------------------------------
// Helpers
// -----------------------------------------
function readLS(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}
function writeLS(key, value) { localStorage.setItem(key, JSON.stringify(value)); }

// Fallback title resolver — UNIVERSAL
function getJobTitle(job) {
  return (
    job.title ||
    job.name ||
    job.position ||
    job.role ||
    job.job_title ||
    "Untitled Role"
  );
}

function jobId(job) {
  // Prefer provided id; otherwise derive from title+company+url
  if (job.id) return String(job.id);

  const raw = `${getJobTitle(job)}|${job.company || ""}|${job.url || ""}`;
  return btoa(unescape(encodeURIComponent(raw))).slice(0, 24);
}

function getSaved() { return readLS(LS_SAVED, []); }
function getHidden() { return new Set(readLS(LS_HIDDEN, [])); }

function setSaved(arr) { writeLS(LS_SAVED, arr); updateSavedCount(); }
function setHidden(setObj) { writeLS(LS_HIDDEN, Array.from(setObj)); }

function updateSavedCount() {
  savedCountEl.textContent = getSaved().length;
}

// Alerts
function showAlert(kind, msg) {
  alertEl.className = `alert alert-${kind}`;
  alertEl.textContent = msg;
  alertEl.classList.remove("d-none");
}
function hideAlert() { alertEl.classList.add("d-none"); }

function setLoading(on) {
  loadingEl.classList.toggle("d-none", !on);
}

// -----------------------------------------
// Rendering Jobs
// -----------------------------------------
function renderJobs(jobs) {
  const hidden = getHidden();
  const hideEnabled = $("#toggleHidden").checked;

  resultsEl.innerHTML = "";

  const visible = jobs.filter(j => (hideEnabled ? !hidden.has(jobId(j)) : true));

  if (visible.length === 0) {
    resultsEl.innerHTML = `<div class="text-muted text-center py-5">No jobs to display.</div>`;
    return;
  }

  for (const job of visible) {
    const id = jobId(job);
    const title = getJobTitle(job);
    const saved = getSaved().some(j => jobId(j) === id);

    const card = document.createElement("div");
    card.className = "col-12 col-md-6 col-xl-4";
    card.innerHTML = `
      <div class="card h-100 shadow-sm">
        <div class="card-body d-flex flex-column">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h5 class="card-title me-2">${escapeHTML(title)}</h5>
            <button class="btn btn-sm ${saved ? "btn-success" : "btn-outline-success"} btn-save" data-id="${id}">
              <i class="bi ${saved ? "bi-bookmark-check" : "bi-bookmark"}"></i>
            </button>
          </div>
          <h6 class="card-subtitle mb-2 text-muted">${escapeHTML(job.company || "Unknown Company")}</h6>
          <div class="small mb-2"><i class="bi bi-geo-alt"></i> ${escapeHTML(job.location || "Remote/Unspecified")}</div>

          ${
            Array.isArray(job.skills) && job.skills.length
              ? `<div class="mb-3">${job.skills
                  .slice(0,8)
                  .map(s => `<span class="badge text-bg-light me-1 mb-1">${escapeHTML(s)}</span>`)
                  .join("")}</div>`
              : ""
          }

          <div class="mt-auto d-flex gap-2">
            ${
              job.url
                ? `<a class="btn btn-primary btn-sm flex-grow-1" href="${escapeAttr(job.url)}" target="_blank" rel="noopener">View</a>`
                : ""
            }
            <button class="btn btn-outline-secondary btn-sm flex-grow-1 btn-hide" data-id="${id}">
              <i class="bi bi-eye-slash"></i> Hide
            </button>
          </div>
        </div>
        ${
          job.posted_at
            ? `<div class="card-footer small text-muted">Posted: ${escapeHTML(job.posted_at)}</div>`
            : ""
        }
      </div>
    `;

    resultsEl.appendChild(card);
  }

  // Hide button handlers
  resultsEl.querySelectorAll(".btn-hide").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const hidden = getHidden();
      hidden.add(id);
      setHidden(hidden);
      renderJobs(currentJobs);
    });
  });

  // Save/Unsave handlers
  resultsEl.querySelectorAll(".btn-save").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const existing = getSaved();
      const found = existing.find(j => jobId(j) === id);

      if (found) {
        setSaved(existing.filter(j => jobId(j) !== id));
      } else {
        const job = currentJobs.find(j => jobId(j) === id);
        if (job) setSaved([job, ...existing]);
      }

      renderJobs(currentJobs);
      renderSavedList();
    });
  });
}


// -----------------------------------------
// Saved List Drawer
// -----------------------------------------
function renderSavedList() {
  const container = $("#savedList");
  const saved = getSaved();

  container.innerHTML = saved.length
    ? ""
    : `<div class="text-muted">No saved jobs yet.</div>`;

  for (const job of saved) {
    const id = jobId(job);
    const title = getJobTitle(job);

    const div = document.createElement("div");
    div.className = "card shadow-sm";
    div.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <h6 class="mb-1">${escapeHTML(title)}</h6>
            <div class="small text-muted">
              ${escapeHTML(job.company || "")}
              ${job.location ? "· " + escapeHTML(job.location) : ""}
            </div>
          </div>
          <div class="d-flex gap-2">
            ${
              job.url
                ? `<a class="btn btn-sm btn-primary" href="${escapeAttr(job.url)}" target="_blank"><i class="bi bi-box-arrow-up-right"></i></a>`
                : ""
            }
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


// -----------------------------------------
// Networking / Search
// -----------------------------------------
async function searchJobs(skills) {
  setLoading(true);
  hideAlert();
  try {
    const res = await fetch("/get_jobs", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `skills=${encodeURIComponent(skills)}`
    });

    const data = await res.json();

    if (Array.isArray(data)) {
      currentJobs = data;
    } else if (Array.isArray(data.jobs)) {
      currentJobs = data.jobs;
    } else {
      currentJobs = [];
      showAlert("warning", "No job list returned.");
    }

    renderJobs(currentJobs);
  } catch (e) {
    showAlert("danger", "Network/server error.");
    console.error(e);
  } finally {
    setLoading(false);
  }
}


// -----------------------------------------
// Initial Event Bindings
// -----------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  updateSavedCount();

  $("#skillForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const skills = $("#skills").value.trim();
    if (!skills) {
      showAlert("warning", "Please enter at least one skill.");
      return;
    }
    searchJobs(skills);
  });

  $("#toggleHidden").addEventListener("change", () => {
    renderJobs(currentJobs);
  });

  $("#btnClearHidden").addEventListener("click", () => {
    setHidden(new Set());
    renderJobs(currentJobs);
  });

  const savedDrawer = new bootstrap.Offcanvas($("#savedDrawer"));
  $("#btnShowSaved").addEventListener("click", () => {
    renderSavedList();
    savedDrawer.show();
  });

  $("#btnClearSaved").addEventListener("click", () => {
    setSaved([]);
    renderSavedList();
    renderJobs(currentJobs);
  });
});


// -----------------------------------------
// Escaping Helpers
// -----------------------------------------
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
